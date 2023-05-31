<template>
    <div v-if="error.statusCode === 404">
        <h1>ERROR</h1>
        <p>{{ error.message }}</p>
    </div>
</template>
<script setup>
const error = useError();
</script>  