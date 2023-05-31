<template>
    <div>
        <h1>state page</h1>
        <h2>{{ title }}</h2>
        <button @click="titleState.changeTitle('Next3')">Nuxt3</button>
    </div>
</template>

<script setup>
const titleState = useTitle();
const { title } = titleState;
</script>