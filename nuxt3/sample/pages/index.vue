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
const url = 'https://jsonplaceholder.typicode.com/users';
const { data: users } = await useFetch(url);
console.log(users);
</script>