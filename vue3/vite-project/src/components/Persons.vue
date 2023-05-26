<script setup lang="ts">
import { ref, Ref } from 'vue';


type Person = {
    id: number,
    name: string,
    age: number
}

let persons: Ref<Person[]> = ref([
    {
        id: Math.random(),
        name: 'test',
        age: 20
    },
    {
        id: Math.random(),
        name: 'test',
        age: 20
    },
    {
        id: Math.random(),
        name: 'test',
        age: 20
    },
]);

const inputName = ref<string>('');
const inputAge = ref<number>(0);
const registerPerson = () => {
    const newPerson = {
        id: Math.random(),
        name: inputName.value,
        age: inputAge.value,
    };
    persons.value = [...persons.value, newPerson];
    console.log(persons);
}
const deletePerson = (id: number) => {
    persons.value = persons.value.filter(person => person.id !== id)
}
</script>

<template>
    <div class="container">
        <h1>テスト</h1>
        <div class="person-form">
            <span for="name">名前：</span>
            <input type="text" v-model="inputName">
            <span for="age">年齢：</span>
            <input type="number" name="age" v-model="inputAge">
            <button @click="registerPerson">送信</button>
        </div>
        <div class="person-list">
            <ul>
                <li v-for="person in persons" :key="person.id">
                    <span>名前：{{ person.name }}</span>
                    <span>年齢：{{ person.age }}</span>
                    <button @click="deletePerson(person.id)">削除</button>
                </li>
            </ul>
        </div>
    </div>
</template>

<style>
.container {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>