import { createRouter, createWebHashHistory } from 'vue-router'
import HomePage from '@/pages/home/HomePage.vue'
import LibraryPage from '@/pages/library/LibraryPage.vue'
import TaskListPage from '@/pages/task/TaskListPage.vue'
import TaskPage from '@/pages/task/TaskPage.vue'
import SettingsPage from '@/pages/settings/SettingsPage.vue'
import SearchPage from '@/pages/search/SearchPage.vue'

const NotePage = () => import('@/pages/note/NotePage.vue')
const MediaPage = () => import('@/pages/media/MediaPage.vue')

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: { crumb: '工作台 / 新建笔记', title: '新建笔记' },
    },
    {
      path: '/notes/:id/:tab?',
      name: 'note',
      component: NotePage,
      meta: { crumb: '笔记库 / 线性代数第 12 讲', title: '笔记详情' },
    },
    {
      path: '/library',
      name: 'library',
      component: LibraryPage,
      meta: { crumb: '笔记库', title: '笔记库' },
    },
    {
      path: '/search',
      name: 'search',
      component: SearchPage,
      meta: { crumb: '搜索笔记', title: '搜索笔记' },
    },
    {
      path: '/media',
      name: 'media',
      component: MediaPage,
      meta: { crumb: '视频区', title: '视频区' },
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: TaskListPage,
      meta: { crumb: '任务', title: '任务' },
    },
    {
      path: '/tasks/:id',
      name: 'task',
      component: TaskPage,
      meta: { crumb: '任务 / 执行详情', title: '任务详情' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsPage,
      meta: { crumb: '设置', title: '设置' },
    },
  ],
})

export default router
