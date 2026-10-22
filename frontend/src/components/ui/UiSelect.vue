<script lang="ts">
import { defineComponent, Fragment, h, onBeforeUnmount, onMounted, onUpdated, ref, useId, type PropType, type VNode } from 'vue'
import { ElOption, ElSelect } from 'element-plus/es/components/select/index'

type Value = string | number | boolean
function options(nodes: VNode[]): VNode[] {
  return nodes.flatMap(node => node.type === Fragment ? options(node.children as VNode[]) : node.type === 'option' ? [node] : [])
}
function text(children: VNode['children']): string {
  if (typeof children === 'string') return children
  return Array.isArray(children) ? children.map(child => typeof child === 'object' && child && 'children' in child ? text((child as VNode).children) : typeof child === 'string' ? child : '').join('') : ''
}

// Keep a form-associated select for required validation and native form submission.
// The visible control, option list and keyboard navigation are Element Plus.
export default defineComponent({
  inheritAttrs: false,
  props: {
    modelValue: { type: [String, Number, Boolean] as PropType<Value>, default: undefined },
    value: { type: [String, Number, Boolean] as PropType<Value>, default: undefined },
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { attrs, slots, emit, expose }) {
    const control = ref<InstanceType<typeof ElSelect>>()
    const proxy = ref<HTMLSelectElement>()
    const inheritedDisabled = ref(false)
    let fieldsets: MutationObserver | undefined
    function syncDisabled() { inheritedDisabled.value = proxy.value?.matches(':disabled') ?? false }
    const invalid = ref(false), validationId = useId() + '-validation'
    const focus = () => control.value?.focus()
    expose({ focus })
    function accessibility() {
      const input = control.value?.$el.querySelector('input') as HTMLInputElement | null
      if (!input) return
      for (const name of ['aria-describedby', 'aria-invalid', 'aria-labelledby', 'data-initial-focus']) {
        const value = name === 'aria-invalid' && invalid.value ? 'true' : name === 'aria-describedby' && invalid.value ? [attrs[name], validationId].filter(Boolean).join(' ') : attrs[name]
        if (value !== undefined && value !== false) input.setAttribute(name, String(value))
        else input.removeAttribute(name)
      }
    }
    onMounted(() => {
      accessibility(); syncDisabled()
      fieldsets = new MutationObserver(syncDisabled)
      for (let parent = proxy.value?.parentElement; parent; parent = parent.parentElement) {
        if (parent.tagName === 'FIELDSET') fieldsets.observe(parent, { attributes: true, attributeFilter: ['disabled'] })
      }
    })
    onUpdated(() => { accessibility(); syncDisabled() })
    onBeforeUnmount(() => fieldsets?.disconnect())
    return () => {
      const children = slots.default?.() ?? []
      const entries = options(children).map(node => ({ value: (node.props?.value ?? text(node.children)) as Value, label: text(node.children), disabled: node.props?.disabled === '' || !!node.props?.disabled }))
      const current = props.modelValue ?? props.value ?? ''
      const change = (event: Event) => {
        if (proxy.value?.matches(':disabled')) return
        const raw = (event.target as HTMLSelectElement).value
        const value = entries.find(option => String(option.value) === raw)?.value ?? raw
        invalid.value = false
        emit('update:modelValue', value); emit('change', event)
      }
      return h('div', { class: ['ui-select-field', attrs.class], style: attrs.style }, [
        h(ElSelect, { ...attrs, ref: control, class: 'ui-select', style: undefined, modelValue: current, disabled: inheritedDisabled.value || attrs.disabled === '' || !!attrs.disabled, teleported: true,
          'onUpdate:modelValue': (value: Value) => {
            if (!proxy.value || proxy.value.matches(':disabled')) return
            proxy.value.value = String(value)
            proxy.value.dispatchEvent(new Event('change', { bubbles: true }))
          },
        }, { default: () => entries.map(option => h(ElOption, { key: String(option.value), ...option })) }),
        h('select', { ref: proxy, class: 'ui-select-proxy', 'data-select-id': attrs.id, value: String(current), name: attrs.name, form: attrs.form, required: attrs.required === '' || !!attrs.required, disabled: attrs.disabled === '' || !!attrs.disabled, tabindex: -1, 'aria-hidden': 'true', onChange: change,
          onInvalid: (event: Event) => {
            event.preventDefault(); invalid.value = true
            const firstInvalid = proxy.value?.form && Array.from(proxy.value.form.elements).find(element => 'validity' in element && !(element as HTMLInputElement).validity.valid)
            if (!proxy.value?.form || firstInvalid === proxy.value) focus()
          },
        }, children),
        invalid.value ? h('p', { id: validationId, class: 'field-error', role: 'alert' }, '请选择此项。') : null,
      ])
    }
  },
})
</script>
