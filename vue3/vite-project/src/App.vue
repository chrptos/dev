<script setup lang="ts">
import { ref } from 'vue'
import TweetPostForm from './components/TweetPostForm.vue';
import TweetPostList from './components/TweetPostList.vue';


const tweets = ref([
  { id: 1, description: 'Hello, World1' },
  { id: 2, description: 'Hello, World2' },
  { id: 3, description: 'Hello, World3' },
  { id: 4, description: 'Hello, World4' },
])

const postTweet = (description: string) => {
  const newTweet = {
    id: Math.random(),
    description: description
  };
  tweets.value = [...tweets.value, newTweet];
};

const deleteTweet = (id: number) => {
  tweets.value = tweets.value.filter(tweet => tweet.id !== id);
};


</script>

<template>
  <div class="container">
    <h1>Twitter</h1>
    <TweetPostForm :tweets="tweets" @post-tweet="postTweet" />
    <TweetPostList :tweets="tweets" @delete-tweet="deleteTweet" />
  </div>
</template>

<style scoped>
.container {
  display: flex;
  align-items: center;
  flex-direction: column;
}
</style>