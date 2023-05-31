<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
<script setup>
useHead(
  {
    title: 'Nuxt 3 Store',
    link: [
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Monomaniac+One&display=swap" }
    ]
  }
)
</script>