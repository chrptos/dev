<script setup lang="ts">
import { ref, defineEmits } from 'vue';

const emit = defineEmits(['registerPerson']);

const inputName = ref<string>('');
const inputAge = ref<number>(0);

const registerPerson = () => {
    const person = { id: Math.random(), name: inputName.value, age: inputAge.value };
    emit('registerPerson', person);
}

</script>

<template>
    <div class="person-form">
        <span for="name">名前：</span>
        <input type="text" v-model="inputName">
        <span for="age">年齢：</span>
        <input type="number" name="age" v-model="inputAge">
        <button @click="registerPerson">送信</button>
    </div>
</template>

<style></style>