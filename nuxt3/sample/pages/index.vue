<template>
    <div>
        <h1>top page</h1>
        <ul>
            <li v-for="user in users" :key="user.id">
                {{ user.id }}, {{ user.name }}
            </li>
        </ul>
    </div>
</template>
<script setup>
const url = 'https://jsonplaceholder.typicode.com/usersa';
const { data: users, error } = await useFetch(url);
if (error.value) {
    throw createError({ statusCode: 404, statusMessage: 'Page not found.' });
}
</script>
