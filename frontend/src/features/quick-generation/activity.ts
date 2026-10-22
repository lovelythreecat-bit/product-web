import { ref } from 'vue'
// A revision signal carries no account data; readers always reload owner-scoped APIs.
export const quickGenerationRevision = ref(0)
