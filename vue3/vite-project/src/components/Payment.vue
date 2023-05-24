<script setup lang="ts">
import { reactive, toRefs, watch, ref } from 'vue'

const tweets = ref([
    { id: 1, description: 'Hello, World1' },
    { id: 2, description: 'Hello, World2' },
    { id: 3, description: 'Hello, World3' },
    { id: 4, description: 'Hello, World4' },
])
const description = ref<string>('');

const postTweet = () => {
    const newTweet = {
        id: Math.random(),
        description: description.value
    };
    tweets.value = [...tweets.value, newTweet];
};

const deleteTweet = (id: number) => {
    tweets.value = tweets.value.filter(tweet => tweet.id !== id)
};

</script>

<template>
    <div class="container">
        <h1>Twitter</h1>
        <div class="form-container">
            <input v-model="description" />
            <button @click="postTweet">ツイート</button>
        </div>
        <div v-if="tweets.length <= 0">
            {{ 'No Tweets!!' }}
        </div>
        <div class="tweet-container">
            <ul>
                <li v-for="tweet in tweets" :key="tweet.id">
                    <span>{{ "ID:" + tweet.id + "ツイート:" + tweet.description }}</span>
                    <button @click="deleteTweet(tweet.id)">削除</button>
                </li>
            </ul>
        </div>
    </div>
</template>

<style scoped>
label {
    font-size: 20px;
}

.container {
    display: flex;
    align-items: center;
    flex-direction: column;
}

.form-container {
    display: flex;
    align-items: center;
    flex-direction: row;
    justify-content: space-around;
}

.form-container input {
    flex-grow: 1;
    margin-right: 10px;
}
</style>