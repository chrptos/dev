<script setup lang="ts">
import { defineProps } from 'vue';
import { Person } from './Persons.vue'

// Props
type Props = {
    persons: Person[]
}
defineProps<Props>();

// Emit
const emit = defineEmits(['deletePerson']);
const deletePerson = (id: number) => {
    emit('deletePerson', id);
}
</script>

<template>
    <ul>
        <li v-for="person in persons" :key="person.id">
            <span>名前：{{ person.name }}</span>
            <span>年齢：{{ person.age }}</span>
            <button @click="deletePerson(person.id)">削除</button>
        </li>
    </ul>
</template>

<style></style>