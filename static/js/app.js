import { createApp, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import * as Api from './api.js?v=3';
import { TOPICS } from './topics.js?v=2'; // Убедитесь, что этот файл существует


const app = createApp({
    data() {
        return {
            // Auth
            token: localStorage.getItem('olymp_token') || null,
            authForm: { username: '', password: '', email: '', grade: 9 },
            userStats: {
                username: 'Guest', level: 1, xp: 0, rating: 1000,
                wins: 0, grade: 9, achievements: []
            },

            // Navigation State
            state: 'login', // login, register, forgot, menu, profile, topic_select, training_solve, pvp_setup, searching, vs, playing, finished

            // Profile
            profileTab: 'analytics',
            history: [],
            historyPage: 0,
            analyticsData: null,
            charts: { winRate: null, topics: null },

            // Training
            subject: 'python',
            selectedDifficulty: 1,
            activeTask: null,
            currentAnswerInput: '',
            solveResult: null,
            revealedHints: [],

            // PvP
            ws: null,
            opponentName: '',
            opponentRating: 0,
            vsTimer: 5,
            task: {}, // PvP Task
            timeLeft: 0,
            myScore: 0,
            enemyScore: 0,
            roundFinished: false,
            roundResult: {},
            nextRoundTimer: 0,
            finalData: {},
            answerSent: false
        }
    },
    computed: {
        currentTopics() {
            const list = TOPICS[this.subject] || [];
            return list.filter(t => this.userStats.grade >= t.minGrade);
        },
        paginatedHistory() {
            const start = this.historyPage * 5;
            return this.history.slice(start, start + 5);
        }
    },
    watch: {
        // Следим за состоянием для обновления URL
        state(newVal) {
            const path = newVal === 'menu' ? '/' : `/${newVal}`;
            if (location.pathname !== path) {
                history.pushState({ state: newVal }, '', path);
            }
            // Инициализация графиков при входе в профиль
            if (newVal === 'profile') {
                this.loadProfileData();
            }
        }
    },
    async mounted() {
        // Обработка кнопки "Назад" в браузере
        window.onpopstate = (event) => {
            if (event.state && event.state.state) {
                this.state = event.state.state;
            } else {
                this.state = this.token ? 'menu' : 'login';
            }
        };

        // Проверка сессии
        if (this.token) {
            try {
                this.userStats = await Api.getUserStats(this.token);
                this.state = 'menu';
            } catch {
                this.logout();
            }
        } else {
            this.state = 'login';
        }
    },
    methods: {
        // === Навигация ===
        goTo(newState) {
            this.state = newState;
        },

        // === Авторизация ===
        async login() {
            try {
                const d = await Api.loginUser(this.authForm.username, this.authForm.password);
                this.token = d.access_token;
                localStorage.setItem('olymp_token', this.token);
                this.userStats = await Api.getUserStats(this.token);
                this.goTo('menu');
            } catch (e) { alert("Ошибка входа"); }
        },
        async register() {
            try {
                await Api.registerUser(this.authForm);
                await this.login();
            } catch (e) { alert("Ошибка регистрации"); }
        },
        logout() {
            this.token = null;
            localStorage.removeItem('olymp_token');
            if(this.ws) this.ws.close();
            this.goTo('login');
        },

        // === Профиль и Графики ===
        async loadProfileData() {
            try {
                const [hist, analytics] = await Promise.all([
                    Api.getHistory(this.token),
                    Api.getAnalytics(this.token)
                ]);
                this.history = hist;
                this.analyticsData = analytics;

                await nextTick(); // Ждем рендеринга DOM
                this.renderCharts();
            } catch (e) { console.error(e); }
        },

        renderCharts() {
            // Очистка старых
            if(this.charts.winRate) this.charts.winRate.destroy();
            if(this.charts.topics) this.charts.topics.destroy();

            const ad = this.analyticsData;
            if (!ad) return;

            // Doughnut Chart (Win/Loss)
            const ctx1 = document.getElementById('winRateChart');
            if (ctx1) {
                const losses = ad.total_matches - this.userStats.wins; // Примерно
                this.charts.winRate = new Chart(ctx1, {
                    type: 'doughnut',
                    data: {
                        labels: ['Победы', 'Поражения/Ничьи'],
                        datasets: [{
                            data: [this.userStats.wins, losses > 0 ? losses : 0],
                            backgroundColor: ['#00e5ff', '#ff0055'],
                            borderWidth: 0
                        }]
                    },
                    options: { plugins: { legend: { display: false } } }
                });
            }

            // Bar Chart (Темы)
            const ctx2 = document.getElementById('topicsChart');
            if (ctx2 && ad.subject_stats && ad.subject_stats.topics) {
                const topics = Object.keys(ad.subject_stats.topics);
                const counts = Object.values(ad.subject_stats.topics);
                this.charts.topics = new Chart(ctx2, {
                    type: 'bar',
                    data: {
                        labels: topics,
                        datasets: [{
                            label: 'Решено задач',
                            data: counts,
                            backgroundColor: 'rgba(0, 229, 255, 0.5)',
                            borderColor: '#00e5ff',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: { y: { beginAtZero: true, grid: { color: '#333' } }, x: { grid: { display: false } } },
                        plugins: { legend: { display: false } }
                    }
                });
            }
        },

        formatDate(dateStr) {
            return new Date(dateStr).toLocaleDateString();
        },
        getMyResult(match) {
            const myName = this.userStats.username;

            let myScore = 0, enemyScore = 0;
            if (match.player1 && match.player1.username === myName) {
                myScore = match.p1_score; enemyScore = match.p2_score;
            } else {
                myScore = match.p2_score; enemyScore = match.p1_score;
            }
            if (myScore > enemyScore) return 'win';
            if (myScore < enemyScore) return 'lose';
            return 'draw';
        },
        getResultText(match) {
            const res = this.getMyResult(match);
            return res === 'win' ? 'WIN' : res === 'lose' ? 'LOSE' : 'DRAW';
        },

        // === Тренировка ===
        async selectTopic(topicId) {
            this.state = 'loading_ai';
            try {
                this.activeTask = await Api.generateAiTask(
                    this.token, this.subject, this.userStats.grade, topicId, this.selectedDifficulty
                );
                this.solveResult = null;
                this.currentAnswerInput = '';
                this.revealedHints = [];
                this.state = 'training_solve';
            } catch (e) {
                alert("Ошибка генерации: " + e.message);
                this.state = 'topic_select';
            }
        },

        async handleAnswer(ans) {
            if (this.state === 'training_solve') {
                if (!ans) return;
                const res = await Api.solveTask(this.token, this.activeTask.id, ans);
                this.solveResult = res.status;
                if (res.status === 'correct') {
                    this.activeTask.is_solved = true;
                }
            } else if (this.state === 'playing') {
                // PvP
                if (this.answerSent) return;
                this.ws.send(JSON.stringify({ answer: ans }));
                this.answerSent = true;
            }
        },

        async useHint() {
            if (this.revealedHints.length >= this.activeTask.hints_available) return;
            try {
                const num = this.revealedHints.length + 1;
                    const d = await Api.getHint(this.token, this.activeTask.id, num);
                this.revealedHints.push(d.hint_text);
            } catch(e) {}
        },

        // === PvP ===
        reset() {
            if(this.ws) this.ws.close();
            this.goTo('menu');
        },

        startPvP() {
            this.goTo('searching');
            const proto = location.protocol === 'https:' ? 'wss' : 'ws';
            this.ws = new WebSocket(`${proto}://${location.host}/ws/pvp?subject=${this.subject}&token=${this.token}`);

            this.ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                if (d.type === 'match_found') {
                    this.opponentName = d.opponent;
                    this.opponentRating = d.rating || '???';
                    this.vsTimer = d.time || 5;
                    this.goTo('vs');
                    const intv = setInterval(() => {
                        this.vsTimer--;
                        if(this.vsTimer <= 0) clearInterval(intv);
                    }, 1000);
                } else if (d.type === 'round_start') {
                    this.state = 'playing';
                    this.task = {
                        title: d.title, description: d.desc,
                        difficulty: d.difficulty, task_type: d.task_type, options: d.options
                    };
                    this.roundFinished = false;
                    this.answerSent = false;
                    this.currentAnswerInput = '';
                    this.timeLeft = '∞';
                } else if (d.type === 'pressure_timer') {
                    this.timeLeft = d.seconds;
                    // Таймер запускается локально для визуализации
                    const tInt = setInterval(() => {
                        if (typeof this.timeLeft === 'number') this.timeLeft--;
                        if (this.timeLeft <= 0 || this.state !== 'playing') clearInterval(tInt);
                    }, 1000);
                } else if (d.type === 'round_result') {
                    this.roundFinished = true;
                    this.roundResult = { you: d.you, enemy: d.enemy, correct: d.correct_answer };
                    if (d.you === 'correct') this.myScore++;
                    if (d.enemy === 'correct') this.enemyScore++;
                    this.nextRoundTimer = 4;
                    const nInt = setInterval(() => {
                        this.nextRoundTimer -= 0.1;
                        if(this.nextRoundTimer <= 0) clearInterval(nInt);
                    }, 100);
                } else if (d.type === 'game_over') {
                    this.finalData = d;
                    this.goTo('finished');
                    this.ws.close();
                } else if (d.type === 'error') {
                    alert(d.message);
                    this.reset();
                }
            };
        },

        renderMath(text) {
            // Простой рендер, если MathJax не загрузился или для быстродействия
            if (!text) return '';
            return text.replace(/\$(.*?)\$/g, '<i>$1</i>');
        }
    }
});

// Глобальная функция для кнопки PvP в меню, так как setup в goTo
app.config.globalProperties.goTo = function(page) {
    if (page === 'pvp_setup') {
        // Упрощаем: сразу старт поиска, или можно сделать экран выбора предмета для пвп
        this.subject = 'python'; // По дефолту или спросить
        this.startPvP();
    } else {
        this.state = page;
    }
}

app.mount('#app');