<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElTable, ElTableColumn } from 'element-plus/es/components/table/index'
import UiButton from '../../components/ui/UiButton.vue'
import UiInput from '../../components/ui/UiInput.vue'
import UiSelect from '../../components/ui/UiSelect.vue'
import AppDrawer from '../../components/AppDrawer.vue'
import AppDialog from '../../components/AppDialog.vue'
import UiPagination from '../../components/ui/UiPagination.vue'
import { userLedger } from '../../api/admin'
import * as api from '../../api/adminUsers'
import { ApiError } from '../../api/client'
import type { Schema } from '../../types/api'
import { session } from '../auth/session'
import { useAdminRequest, date } from './shared'
import { ledgerKinds } from './display'
const {busy,error,run,current}=useAdminRequest()
const users=ref<api.ManagedUser[]>([]),keyword=ref(''),status=ref(''),notice=ref('')
const page=ref(1),total=ref(0)
let appliedKeyword='',appliedStatus=''
const selected=ref<api.ManagedUser|null>(null),detailOpen=ref(false),editOpen=ref(false),resetOpen=ref(false),deleteOpen=ref(false),adjustOpen=ref(false),confirmOpen=ref(false)
const edit=ref<api.UserEdit|null>(null),password=ref(''),confirmPassword=ref(''),reason=ref(''),delta=ref<number|string>(0)
const pending=ref<api.AdjustmentIntent|null>(null)
const actor=session.profile.value!.user_id
const ledgerOpen=ref(false),ledger=ref<Schema<'LedgerEntryView'>[]>([]),ledgerPage=ref(1),ledgerTotal=ref(0),ledgerUser=ref<api.ManagedUser|null>(null)
async function load(target=1,reset=false){
 const q=reset?keyword.value.trim():appliedKeyword,filter=reset?status.value:appliedStatus
 return run(()=>api.listUsers(undefined,filter||undefined,q||undefined,target),result=>{
  if(reset){appliedKeyword=q;appliedStatus=filter}
  users.value=result.items;total.value=result.total;page.value=result.page??target
 })
}
function clear(){keyword.value='';status.value='';void load(1,true)}
async function open(user:api.ManagedUser,kind:'detail'|'edit'|'reset'|'delete'|'adjust'){
 if(busy.value)return
 reason.value='';password.value='';confirmPassword.value='';error.value=''
 await run(()=>api.getUser(user.id),fresh=>{
  selected.value=fresh
  if(kind==='detail')detailOpen.value=true
  if(kind==='edit'){
   edit.value={expected_auth_version:fresh.auth_version,expected_profile_version:fresh.profile_version,account:fresh.account_normalized,nickname:fresh.nickname,shop_name:fresh.shop_name??null,category:fresh.category??null,email:fresh.email??null,phone:fresh.phone??null,role:fresh.role,status:fresh.status,reason:''};editOpen.value=true
  }
  if(kind==='reset')resetOpen.value=true
  if(kind==='delete'&&fresh.role!=='admin')deleteOpen.value=true
  if(kind==='adjust'){delta.value=0;adjustOpen.value=true}
 })
}
async function saveEdit(){
 if(!selected.value||!edit.value)return
 const ok=await run(()=>api.updateUser(selected.value!.id,{...edit.value!,reason:edit.value!.reason.trim()}),()=>{editOpen.value=false;notice.value='用户信息已保存。'})
 if(ok)await load(page.value)
}
async function savePassword(){
 if(!selected.value)return
 if(password.value!==confirmPassword.value){error.value='两次输入的新密码不一致。';return}
 const ok=await run(()=>api.resetPassword(selected.value!.id,{expected_auth_version:selected.value!.auth_version,new_password:password.value,reason:reason.value.trim()}),()=>{resetOpen.value=false;password.value='';confirmPassword.value='';notice.value='密码已重置，该用户原登录已退出。'})
 if(ok)await load(page.value)
}
async function remove(){
 if(!selected.value||selected.value.role==='admin')return
 const ok=await run(()=>api.deleteUser(selected.value!.id,{expected_auth_version:selected.value!.auth_version,reason:reason.value.trim()}),()=>{deleteOpen.value=false;notice.value='用户已删除，历史任务、积分流水和审计记录已保留。'})
 if(ok)await load(1,true)
}
function confirmAdjustment(){
 const value=Number(delta.value)
 if(!Number.isSafeInteger(value)||value===0||!reason.value.trim()){error.value='请填写非零整数积分和调整原因；减少积分请填负数。';return}
 confirmOpen.value=true
}
async function sendAdjustment(){
 if(busy.value)return
 try{if(!pending.value&&selected.value)pending.value=api.rememberAdjustment(actor,selected.value.id,Number(delta.value),reason.value.trim())}
 catch(e){error.value=e instanceof Error?e.message:'无法保存调整记录，本次未发送。';return}
 if(!pending.value)return
 const intent=pending.value
 const ok=await run(async()=>{
  try{
   const receipt=await api.adjustCredits(intent)
   if(receipt.business_key!==intent.body.business_key||receipt.user_id!==intent.user_id||receipt.actor_id!==actor||receipt.delta!==intent.body.delta||receipt.reason!==intent.body.reason||!receipt.ledger_id)throw Error('回执无法确认原调整，请保留业务标识并重试原请求。')
   return receipt
  }catch(e){
   if(current()&&e instanceof ApiError&&e.code==='ADJUSTMENT_TARGET_DELETED'){
    api.forgetAdjustment(actor,intent.body.business_key);pending.value=null
    confirmOpen.value=false;adjustOpen.value=false
    throw Error('目标用户已删除，本次积分未调整。')
   }
   // Explicit input/insufficient-funds responses prove this attempt was rejected.
   if(current()&&e instanceof ApiError&&[402,422].includes(e.status)){api.forgetAdjustment(actor,intent.body.business_key);pending.value=null}
   throw e
  }
 },receipt=>{api.forgetAdjustment(actor,receipt.business_key);pending.value=null;confirmOpen.value=false;adjustOpen.value=false;notice.value='积分调整已完成：'+(receipt.delta>0?'+':'')+receipt.delta+' 积分。'})
 if(ok)await load(page.value)
}
async function openLedger(user:api.ManagedUser){
 if(busy.value)return
 ledgerUser.value=user;ledger.value=[];ledgerPage.value=1;ledgerTotal.value=0;ledgerOpen.value=true
 await loadLedger(1)
}
function loadLedger(target:number){
 if(!ledgerUser.value)return
 const user=ledgerUser.value.id
 return run(()=>userLedger(user,undefined,target),result=>{if(ledgerUser.value?.id!==user)return;ledger.value=result.items;ledgerPage.value=result.page??target;ledgerTotal.value=result.total})
}
onMounted(()=>{try{pending.value=api.restoreAdjustment(actor)}catch(e){error.value=e instanceof Error?e.message:'待确认记录不可读。';return}void load(1,true)})
const UserColumn=ElTableColumn<api.ManagedUser>
const LedgerColumn=ElTableColumn<Schema<'LedgerEntryView'>>
</script>
<template>
 <div class="admin-page admin-list-page">

  <p v-if="error" class="field-error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
  <p v-if="pending" class="pending-adjustment" role="status">有一笔积分调整待确认：{{ pending.body.delta > 0 ? '+' : '' }}{{ pending.body.delta }} 积分 · {{ pending.body.reason }}<UiButton class="button" :disabled="busy" @click="sendAdjustment">重试原积分调整</UiButton></p>
  <section class="panel admin-list-panel" aria-label="用户管理列表">
   <form class="admin-filters" @submit.prevent="load(1,true)">
    <label for="admin-user-keyword">账号 / 昵称 / 店铺<UiInput id="admin-user-keyword" v-model="keyword" maxlength="128" placeholder="输入关键词" /></label>
    <label>账户状态<UiSelect v-model="status"><option value="">全部</option><option value="active">正常</option><option value="disabled">已停用</option></UiSelect></label>
    <UiButton class="button primary" :disabled="busy">查询</UiButton><UiButton type="button" class="button" :disabled="busy" @click="clear">清空</UiButton>
   </form>
   <div class="admin-table admin-list-table" role="region" aria-label="用户列表" :aria-busy="busy">
    <ElTable :data="users" row-key="id" height="100%" class="ui-data-table" empty-text="暂无匹配用户" border>
     <UserColumn label="账号" :min-width="150" prop="account_normalized" />
     <UserColumn label="昵称" :min-width="120"><template #default="{row}">{{ row.nickname || '未填写' }}</template></UserColumn>
     <UserColumn label="店铺" :min-width="150"><template #default="{row}">{{ row.shop_name || '未填写' }}</template></UserColumn>
     <UserColumn label="角色" :min-width="100"><template #default="{row}">{{ row.role==='admin'?'管理员':'普通用户' }}</template></UserColumn>
     <UserColumn label="账户状态" :min-width="100"><template #default="{row}">{{ row.status==='active'?'正常':'已停用' }}</template></UserColumn>
     <UserColumn label="可用积分" :min-width="100" align="right" prop="available" />
     <UserColumn label="操作" :min-width="400"><template #default="{row}"><div class="action-row user-actions">
      <UiButton class="button" :disabled="busy" @click="open(row,'detail')">查看</UiButton><UiButton class="button" :disabled="busy" @click="open(row,'edit')">编辑</UiButton><UiButton class="button" :disabled="busy" @click="open(row,'reset')">重置密码</UiButton><UiButton class="button" :disabled="busy" @click="openLedger(row)">积分流水</UiButton><UiButton class="button" :disabled="busy || !!pending" @click="open(row,'adjust')">积分调整</UiButton><UiButton class="button danger" :disabled="busy || row.role==='admin'" @click="open(row,'delete')">删除</UiButton>
     </div></template></UserColumn>
    </ElTable>
   </div>
   <UiPagination class="admin-pagination" :page="page" :total="total" :disabled="busy" @change="load" />
  </section>
  <AppDrawer v-model:open="detailOpen" title="用户信息" purpose="read"><dl v-if="selected" class="detail-list"><dt>账号</dt><dd>{{ selected.account_normalized }}</dd><dt>昵称</dt><dd>{{ selected.nickname || '未填写' }}</dd><dt>店铺名称</dt><dd>{{ selected.shop_name || '未填写' }}</dd><dt>商品分类</dt><dd>{{ selected.category || '未填写' }}</dd><dt>联系邮箱</dt><dd>{{ selected.email || '未填写' }}</dd><dt>联系电话</dt><dd>{{ selected.phone || '未填写' }}</dd><dt>角色</dt><dd>{{ selected.role==='admin'?'管理员':'普通用户' }}</dd><dt>账户状态</dt><dd>{{ selected.status==='active'?'正常':'停用' }}</dd><dt>注册时间</dt><dd>{{ date(selected.created_at) }}</dd><dt>最近登录</dt><dd>{{ selected.last_login_at?date(selected.last_login_at):'暂无登录记录' }}</dd></dl></AppDrawer>
  <AppDrawer v-model:open="editOpen" title="编辑用户" purpose="edit"><form v-if="edit" id="admin-user-edit" class="form-stack" @submit.prevent="saveEdit">
   <label>账号<UiInput v-model="edit.account" required minlength="3" maxlength="64" data-initial-focus /></label><label>昵称<UiInput v-model="edit.nickname" required maxlength="80" /></label><label>店铺名称（选填）<UiInput v-model="edit.shop_name" maxlength="80" /></label><label>商品分类（选填）<UiInput v-model="edit.category" maxlength="80" /></label><label>联系电话（选填）<UiInput v-model="edit.phone" maxlength="40" /></label><label>联系邮箱（选填）<UiInput v-model="edit.email" type="email" maxlength="120" /></label><label>角色<UiSelect v-model="edit.role" :disabled="selected?.role==='admin'"><option value="user">普通用户</option><option value="admin">管理员</option></UiSelect></label><label>账户状态<UiSelect v-model="edit.status" :disabled="selected?.role==='admin'"><option value="active">正常</option><option value="disabled">停用</option></UiSelect></label><label>操作原因<UiInput v-model="edit.reason" required maxlength="500" /></label><p>保存后将退出该用户的原登录；正在处理的任务和冻结积分继续保留。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p>
  </form><template #actions><UiButton class="button primary" form="admin-user-edit" :disabled="busy">保存</UiButton></template></AppDrawer>
  <AppDrawer v-model:open="resetOpen" title="重置密码" purpose="edit"><form id="admin-user-password" class="form-stack" @submit.prevent="savePassword"><p>账号：{{ selected?.account_normalized }}</p><label>新密码<UiInput v-model="password" type="password" required minlength="10" maxlength="128" autocomplete="new-password" data-initial-focus /></label><label>确认新密码<UiInput v-model="confirmPassword" type="password" required minlength="10" maxlength="128" autocomplete="new-password" /></label><label>重置原因<UiInput v-model="reason" required maxlength="500" /></label><p>密码至少 10 位。重置后原登录立即退出。</p><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" form="admin-user-password" :disabled="busy">确认重置</UiButton></template></AppDrawer>
  <AppDialog v-model:open="deleteOpen" title="删除用户" purpose="delete"><form id="admin-user-delete" class="form-stack" @submit.prevent="remove"><p>确认删除 {{ selected?.account_normalized }}？删除后该用户无法登录，历史任务、积分流水和审计记录将保留。</p><label>删除原因<UiInput v-model="reason" required maxlength="500" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button danger" form="admin-user-delete" :disabled="busy || selected?.role==='admin'">确认删除</UiButton></template></AppDialog>
  <AppDrawer v-model:open="adjustOpen" title="积分调整" purpose="edit"><form id="admin-user-adjustment" class="form-stack" @submit.prevent="confirmAdjustment"><p>{{ selected?.account_normalized }} · 可用 {{ selected?.available }} · 冻结 {{ selected?.frozen }}</p><label>调整积分<UiInput v-model="delta" type="number" step="1" required data-initial-focus /></label><p>增加填正数，减少填负数；仅调整可用积分，冻结积分保持不变。</p><label>调整原因<UiInput v-model="reason" required maxlength="500" /></label><p v-if="error" class="field-error" role="alert">{{ error }}</p></form><template #actions><UiButton class="button primary" form="admin-user-adjustment" :disabled="busy || !!pending">继续</UiButton></template></AppDrawer>
  <AppDialog v-model:open="confirmOpen" title="确认积分调整" purpose="charge"><p>为 {{ selected?.account_normalized }} {{ Number(delta)>0?'增加':'减少' }} {{ Math.abs(Number(delta)) }} 积分。</p><p>{{ reason }}</p><p v-if="error" class="field-error" role="alert">{{ error }}</p><template #actions><UiButton class="button primary" :disabled="busy" @click="sendAdjustment">确认调整</UiButton></template></AppDialog>
  <AppDialog v-model:open="ledgerOpen" :title="'积分流水 · '+(ledgerUser?.account_normalized || '')" purpose="read" class="user-ledger-dialog">
   <div class="user-ledger-content"><p v-if="error" class="field-error" role="alert">{{ error }}</p><div class="user-ledger-table"><ElTable :data="ledger" row-key="ledger_id" height="100%" empty-text="暂无积分流水" class="ui-data-table" border>
    <LedgerColumn label="时间" :min-width="170"><template #default="{row}">{{ date(row.created_at) }}</template></LedgerColumn><LedgerColumn label="类型" :min-width="110"><template #default="{row}">{{ ledgerKinds[row.kind] || row.kind }}</template></LedgerColumn><LedgerColumn label="积分" :min-width="85"><template #default="{row}">{{ ['admin_deduct','freeze','consume'].includes(row.kind)?'-':'+' }}{{ row.amount }}</template></LedgerColumn><LedgerColumn label="变更后可用 / 冻结" :min-width="150"><template #default="{row}">{{ row.balances_after.available }} / {{ row.balances_after.frozen }}</template></LedgerColumn><LedgerColumn label="原因" :min-width="180" prop="reason" />
   </ElTable></div></div><template #actions><UiPagination :page="ledgerPage" :total="ledgerTotal" :disabled="busy" label="用户积分流水分页" @change="loadLedger" /></template>
  </AppDialog>
 </div>
</template>
<style scoped>
.admin-page .admin-table :deep(.el-table__cell) {padding:10px 0}
.admin-page .admin-table :deep(th .cell) {white-space:nowrap;overflow-wrap:normal}
.admin-page .admin-table .user-actions {flex-wrap:nowrap;gap:2px}
.admin-page .admin-table .user-actions .button {flex-shrink:0;min-height:32px;padding:5px 6px;font-size:12px;white-space:nowrap}
@media (max-width:700px), (pointer:coarse) { .admin-page .admin-table .user-actions .button {min-height:44px;padding:8px;font-size:14px} }
.pending-adjustment {display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0;font-size:13px}
.user-ledger-content {height:min(52vh,440px);min-height:160px;display:flex;flex-direction:column;overflow:hidden}
.user-ledger-table {flex:1;min-height:0;overflow:hidden}
</style>
<style>
.user-ledger-dialog.app-overlay.dialog {width:min(1000px,calc(100vw - 32px)) !important}
.user-ledger-dialog .overlay-content {overflow:hidden !important}
.user-ledger-dialog .overlay-actions {flex-wrap:wrap}
</style>
