<script setup lang="ts">
import { defineProps } from 'vue';

type Tweet = {
    id: number,
    description: string,
}

type Props = {
    tweets: Tweet[]
}

const props = defineProps<Props>();

const emit = defineEmits(['delete-tweet']);

const deleteTweet = (id: number) => {
    emit('delete-tweet', id);
};

</script>

<template>
    <ul>
        <li v-for="tweet in props.tweets" :key="tweet.id">
            <span>{{ "ID:" + tweet.id + "ツイート:" + tweet.description }}</span>
            <button @click="deleteTweet(tweet.id)">削除</button>
        </li>
    </ul>
</template>

<style></style>