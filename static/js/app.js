import { createApp, nextTick } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import * as Api from './api.js?v=4';
import { TOPICS } from './topics.js?v=2';

const app = createApp({
    data() {
        return {
            token: localStorage.getItem('olymp_token') || null,
            state: 'login', // Начальное состояние

            // Данные пользователя
            authForm: { username: '', password: '', email: '', grade: 9 },
            userStats: { username: 'GUEST', level: 1, xp: 0, rating: 1000, wins: 0, losses: 0, grade: 9 },

            // Навигация
            profileTab: 'analytics',

            // Данные профиля
            history: [],
            historyPage: 0,
            analyticsData: null,
            charts: { winRate: null, topics: null },

            // Тренировка
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
            task: {},
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
    async mounted() {
        const currentPath = window.location.pathname.replace('/', '');

        if (this.token) {
            try {
                this.userStats = await Api.getUserStats(this.token);

                if (!currentPath || currentPath === 'login') {
                    this.goTo('menu');
                } else {
                    this.goTo(currentPath);
                }
            } catch (e) {
                console.error("Auth check failed:", e);
                this.logout();
            }
        } else {
            this.goTo(currentPath === 'register' ? 'register' : 'login');

        }

        window.onpopstate = (event) => {
            if (event.state && event.state.state) {
                this.state = event.state.state;
                if (this.state === 'training_solve' || this.state === 'playing') {
                    this.triggerMathRender();   }
            }
        };
    },
    methods: {
        goTo(newState) {
            if (['menu', 'topic_select', 'pvp_setup'].includes(newState)) {
                this.activeTask = null;
                this.task = {};
                this.currentAnswerInput = '';
                this.solveResult = null;
                this.revealedHints = [];
                this.roundFinished = false;
                this.answerSent = false;
                this.timeLeft = 0;
            }

            // Переходы
            this.state = newState;
            const path = newState === 'menu' ? '/' : `/${newState}`;
            if (location.pathname !== path) {
                history.pushState({ state: newState }, '', path);
            }

            if (newState === 'profile') this.loadProfileData();

            if (['menu', 'topic_select', 'pvp_setup', 'profile'].includes(newState)) {
                if (this.ws) {
                    this.ws.close();
                    this.ws = null;
                }
            }
        },

        triggerMathRender() {
            nextTick(() => {
                const elem = document.querySelector('.task-desc, .hint-bubble');
                if (elem && window.renderMathInElement) {
                    window.renderMathInElement(elem, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\(', right: '\\)', display: false},
                            {left: '\\[', right: '\\]', display: true}
                        ],
                        throwOnError: false
                    });
                }
            });
        },
        // Авторизация
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

        // Профиль
        async loadProfileData() {
            if (!this.token) return;
            try {
                const [hist, analytics] = await Promise.all([
                    Api.getHistory(this.token),
                    Api.getAnalytics(this.token)
                ]);
                this.history = hist;
                this.analyticsData = analytics;
                await nextTick();
                this.renderCharts();
            } catch (e) { console.error(e); }
        },
        // Графики
        renderCharts() {
            if(this.charts.winRate) this.charts.winRate.destroy();
            if(this.charts.topics) this.charts.topics.destroy();
            const ad = this.analyticsData;
            if (!ad) return;

            Chart.defaults.color = '#889';
            Chart.defaults.borderColor = '#334';

            const ctx1 = document.getElementById('winRateChart');
            if (ctx1) {
                const draws = ad.total_matches - (this.userStats.wins + this.userStats.losses)
                this.charts.winRate = new Chart(ctx1, {
                    type: 'doughnut',
                    data: {
                        labels: ['Победы', 'Пройгрышы', 'Ничьи'],
                        datasets: [{
                            data: [this.userStats.wins, this.userStats.losses , draws],
                            backgroundColor: ['#00f3ff', '#ff0055', '#ffee00'],
                            borderWidth: 0
                        }]
                    },
                    options: { plugins: { legend: { display: false } }, cutout: '70%' }
                });
            }

            const ctx2 = document.getElementById('topicsChart');
            if (ctx2 && ad.subject_stats?.topics) {
                const topics = Object.keys(ad.subject_stats.topics);
                const counts = Object.values(ad.subject_stats.topics);
                this.charts.topics = new Chart(ctx2, {
                    type: 'bar',
                    data: {
                        labels: topics,
                        datasets: [{
                            label: 'Решено',
                            data: counts,
                            backgroundColor: 'rgba(0, 243, 255, 0.2)',
                            borderColor: '#00f3ff',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: { y: { beginAtZero: true }, x: { grid: { display: false } } },
                        plugins: { legend: { display: false } }
                    }
                });
            }
        },


        formatDate(d) { return new Date(d).toLocaleDateString(); },
        getMyResult(m) {
            const me = this.userStats.username;
            const p1 = m.player1?.username;
            const s1 = m.p1_score, s2 = m.p2_score;
            const myScore = p1 === me ? s1 : s2;
            const opScore = p1 === me ? s2 : s1;
            if(myScore > opScore) return 'win';
            if(myScore < opScore) return 'lose';
            return 'draw';
        },
        getResultText(m) {
            const r = this.getMyResult(m);
            return r === 'win' ? 'WIN' : r === 'lose' ? 'LOSE' : 'DRAW';
        },

        // Тренировки
        async selectTopic(topicId) {
            this.state = 'loading_ai';
            try {
                this.activeTask = await Api.generateAiTask(
                    this.token, this.subject, this.userStats.grade, topicId, this.selectedDifficulty
                );
                this.solveResult = null;
                this.currentAnswerInput = '';
                this.revealedHints = [];
                this.goTo('training_solve');
                this.triggerMathRender();
            } catch (e) {
                alert("AI CORE ERROR: " + e.message);
                this.goTo('topic_select');
            }
        },
        async handleAnswer(ans) {
            if (!ans) return;
            if (this.state === 'training_solve') {
                const res = await Api.solveTask(this.token, this.activeTask.id, ans);
                this.solveResult = res.status;
                if (res.status === 'correct') {
                    this.activeTask.is_solved = true;
                }
            } else if (this.state === 'playing') {
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
                this.triggerMathRender()
            } catch(e) {}
        },

        // PVP
        reset() {
            if(this.ws) this.ws.close();
            this.goTo('menu');
        },
        startPvP() {
            if (!this.subject) return alert("SELECT MODULE");
            this.goTo('searching');
            this.myScore = 0; this.enemyScore = 0;

            const proto = location.protocol === 'https:' ? 'wss' : 'ws';
            const url = `${proto}://${location.host}/ws/pvp?subject=${this.subject}&token=${this.token}\\`;
            this.ws = new WebSocket(url);

            this.ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                if (d.type === 'match_found') {
                    this.opponentName = d.opponent;
                    this.opponentRating = d.rating || '???';
                    this.vsTimer = d.time || 5;
                    this.goTo('vs');
                    const t = setInterval(() => {
                        this.vsTimer--;
                        if(this.vsTimer <= 0) clearInterval(t);
                    }, 1000);
                } else if (d.type === 'round_start') {
                    this.goTo('playing');
                    this.task = {
                        title: d.title, description: d.desc,
                        difficulty: d.difficulty, task_type: d.task_type, options: d.options
                    };
                    this.roundFinished = false;
                    this.answerSent = false;
                    this.currentAnswerInput = '';
                    this.timeLeft = '∞';
                    this.triggerMathRender();
                } else if (d.type === 'pressure_timer') {
                    this.timeLeft = d.seconds;
                    const pt = setInterval(() => {
                        if(typeof this.timeLeft === 'number') this.timeLeft--;
                        if(this.timeLeft <= 0 || this.state !== 'playing') clearInterval(pt);
                    }, 1000);
                } else if (d.type === 'round_result') {
                    this.roundFinished = true;
                    this.roundResult = { you: d.you, enemy: d.enemy, correct: d.correct_answer };
                    if (d.you === 'correct') this.myScore++;
                    if (d.enemy === 'correct') this.enemyScore++;

                    this.nextRoundTimer = 4;
                    const nt = setInterval(() => {
                        this.nextRoundTimer -= 0.1;
                        if(this.nextRoundTimer <= 0) clearInterval(nt);
                    }, 100);
                } else if (d.type === 'game_over') {
                    this.finalData = d;
                    this.goTo('finished');
                    this.ws.close();
                    this.ws = null;
                } else if (d.type === 'error') {
                    alert("SYSTEM ERROR: " + d.message);
                    this.reset();
                }
            };

            this.ws.onerror = () => {
                alert("CONNECTION FAILED");
                this.reset();
            };
        }
    }
});
app.mount('#app');