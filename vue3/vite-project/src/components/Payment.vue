<script setup lang="ts">
import { ref } from 'vue'
import TweetPostForm from './TweetPostForm';
import TweetList from './TweetList';


const tweets = ref([
    { id: 1, description: 'Hello, World1' },
    { id: 2, description: 'Hello, World2' },
    { id: 3, description: 'Hello, World3' },
    { id: 4, description: 'Hello, World4' },
])



</script>

<template>
    <div class="container">
        <h1>Twitter</h1>
        <TweetPostForm />
        <div v-if="tweets.length <= 0">
            {{ 'No Tweets!!' }}
        </div>
        <div class="tweet-container">
            <ul>
                <TweetList />
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