import { config } from '@vue/test-utils'
// Business component tests isolate the overlay shell. Dedicated overlay and
// browser tests exercise the real Element Plus portals and focus management.
const overlay = {
  props: ['open', 'title', 'purpose'], emits: ['update:open'],
  template: '<section v-if="open" role="dialog" :aria-label="title"><h2>{{ title }}</h2><slot/><button type="button" @click="$emit(\'update:open\', false)">{{ purpose && purpose !== \'read\' ? \'取消\' : \'关闭\' }}</button><slot name="actions"/></section>',
}
config.global.stubs.AppDrawer = overlay
config.global.stubs.AppDialog = overlay
