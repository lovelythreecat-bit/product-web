<script setup lang="ts">
defineProps<{ name: 'wing' | 'arrow' | 'send' | 'chat' | 'check' | 'book' | 'star' | 'shield' | 'heart' | 'feather' }>()
const paths = {
  wing: 'M3 21c3-9 14-6 18-18-1 10-5 13-12 14M3 21c6-6 12-1 18-10M3 21l-1 2',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  send: 'm21 3-6 18-4-8-8-4 18-6ZM11 13l10-10',
  chat: 'M21 11a9 8 0 0 1-9 8H8l-5 3 1-6a8 8 0 0 1-1-5 9 8 0 0 1 18 0ZM8 11h.01M12 11h.01M16 11h.01',
  check: 'm5 12 4 4L19 6',
  book: 'M12 5v16M12 5C9 3 5 3 2 4v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-1-10 1Z',
  star: 'm12 2 3 6 7 1-5 5 1 8-6-4-6 4 1-8-5-5 7-1 3-6Z',
  shield: 'm12 2 9 4v7c0 5-9 9-9 9S3 18 3 13V6l9-4ZM7 11l5 6 5-6-5-5-5 5Z',
  heart: 'M12 21S2 15 2 8a5 5 0 0 1 10-1 5 5 0 0 1 10 1c0 7-10 13-10 13Z',
  feather: 'M3 21 15 9M8 16C4 7 16 1 21 3c2 5-4 17-13 13ZM11 13l6 1M14 10l5 1',
}
</script>

<template><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name]" /></svg></template>
