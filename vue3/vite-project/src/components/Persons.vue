<script setup lang="ts">
import { computed, ref, Ref } from 'vue';
import PersonInput from './PersonInput.vue';
import PersonList from './PersonList.vue';
import ParentComponent from './ParentComponent.vue';
import component1 from './component1.vue';
import component2 from './component2.vue';

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

let isActiveTabName = ref('1');

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
    if (confirm('削除しますか？')) {
        persons.value = persons.value.filter(person => person.id !== id)
    }
}

// updateTabはclickイベント時にしか呼ばれないから、computedは利用しない。
const updateTab = (name: string) => {
    isActiveTabName.value = name;
}

// 呼ばれる回数によってcomputedを利用するか考える。初期画面で「currentComponent」が毎回呼ばれるので、computedでキャッシュする。
const currentComponent = computed(() => {
    switch (isActiveTabName.value) {
        case '1':
            // componentを返す（文字列ではない）
            return component1;
        case '2':
            return component2;
        default:
            return component1;
    }
});
</script>

<template>
    <div class="container">
        <h1>テスト</h1>
        <PersonInput @registerPerson="registerPerson" />
        <div class="person-list">
            <PersonList :persons="persons" @deletePerson="deletePerson" />
        </div>
        <ParentComponent />
        <button @click="updateTab('1')">1</button>
        <button @click="updateTab('2')">2</button>
        <component :is="currentComponent"></component>
    </div>
</template>

<style>
.container {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>