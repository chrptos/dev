<script setup lang="ts">
import { ref, Ref } from 'vue';
import PersonInput from './PersonInput.vue';
import PersonList from './PersonList.vue';

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

const registerPerson = (person: Person) => {
    const newPerson = {
        id: Math.random(),
        name: person.name,
        age: person.age,
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
        <PersonInput @registerPerson="registerPerson" />
        <div class="person-list">
            <PersonList :persons="persons" @deletePerson="deletePerson" />
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