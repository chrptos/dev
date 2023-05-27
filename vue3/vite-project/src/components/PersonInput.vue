<script setup lang="ts">
import { ref, defineEmits, computed } from 'vue';

const emit = defineEmits(['registerPerson']);

const inputName = ref<string>('');
const inputAge = ref<number>(0);

const registerPerson = () => {
    const person = { id: Math.random(), name: inputName.value, age: inputAge.value };
    emit('registerPerson', person);
}

const nameLengthLimit: number = 15;
const isValidName = computed(() => {
    return inputName.value.length <= nameLengthLimit ? true : false;
});
const color = computed(() => {
    return isValidName.value ? 'black' : 'red';
});

</script>

<template>
    <div class="person-form">
        <span for="name">名前：</span>
        <input class="input__name" type="text" v-model="inputName">
        <span for="age">年齢：</span>
        <input class="input__age" type="number" name="age" v-model="inputAge">
        <button :disabled="!isValidName" @click="registerPerson">送信</button>
    </div>
</template>

<style>
input {
    background-color: v-bind(color);
}
</style>