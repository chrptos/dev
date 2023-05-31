<template>
    <div>
        <h1>page {{ $route.params.id }}</h1>
    </div>
</template>

<script setup>
definePageMeta({
    validate: async (route) => {
        return /^\d+$/.test(route.params.id);
    }
})
</script>