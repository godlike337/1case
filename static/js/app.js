import { createApp } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
// Добавляем ?v=... чтобы браузер точно обновил кэш
import * as Api from './api.js?v=final_fix';
import { TOPICS } from './topics.js?v=final_fix';

createApp({
    data() {
        return {
            // --- АВТОРИЗАЦИЯ ---
            token: localStorage.getItem('olymp_token') || null,
            authForm: { username: '', password: '', email: '', grade: 9 },
            userStats: {
                username: 'Guest', level: 1, xp: 0, rating: 1000,
                wins: 0, grade: 9, achievements: []
            },

            // --- НАВИГАЦИЯ ---
            state: 'menu',
            subject: 'python', // Текущий предмет

            // --- ТРЕНИРОВКА (AI & CATALOG) ---
            trainingTasks: [],
            activeTask: null, // Текущая открытая задача
            trainingAnswer: '',
            solveResult: null,
            revealedHints: [],
            isHintLoading: false,
            selectedDifficulty: 1,

            // --- PVP ДАННЫЕ ---
            ws: null,
            opponentName: '',
            vsTimer: 5,
            task: { title: '', desc: '', difficulty: 1 }, // Задача PvP
            answer: '',
            answerSent: false,
            timeLeft: '∞', // Таймер (строка или число)
            currentRound: 1,
            totalRounds: 3,
            myScore: 0,
            enemyScore: 0,
            roundFinished: false,
            roundResult: {},
            finalData: {},
            nextRoundTimer: 0,

            // --- МОДАЛКИ ---
            showHistory: false,
            historyList: [],
            showAnalytics: false,
            analyticsData: null,

            // --- ТЕХНИЧЕСКОЕ ---
            intervals: { vs: null, game: null, next: null }
        }
    },
    computed: {
        // Фильтруем темы по классу ученика
        currentTopics() {
            const list = TOPICS[this.subject] || [];
            // Если userStats еще не загрузился, считаем класс = 1
            const userGrade = this.userStats.grade || 1;
            return list.filter(t => userGrade >= t.minGrade);
        }
    },
    mounted() {
        if (this.token) this.fetchStats();
    },
    methods: {
        // ===========================================
        // 1. УТИЛИТЫ
        // ===========================================

        // Очистка всех таймеров (чтобы не тикали в фоне)
        clearTimers() {
            Object.values(this.intervals).forEach(clearInterval);
        },

        // ===========================================
        // 2. АВТОРИЗАЦИЯ
        // ===========================================
        async fetchStats() {
            try { this.userStats = await Api.getUserStats(this.token); }
            catch { this.logout(); }
        },
        async login() {
            try {
                const d = await Api.loginUser(this.authForm.username, this.authForm.password);
                this.token = d.access_token;
                localStorage.setItem('olymp_token', this.token);
                await this.fetchStats();
            } catch { alert("Ошибка входа: неверный логин или пароль"); }
        },
        async register() {
            try {
                await Api.registerUser(this.authForm);
                await this.login();
            } catch { alert("Ошибка регистрации: имя занято"); }
        },
        logout() {
            this.clearTimers();
            this.token = null;
            localStorage.removeItem('olymp_token');
            if(this.ws) this.ws.close();
            this.state = 'menu';
        },
        reset() {
            this.clearTimers();
            if(this.ws) this.ws.close();
            this.state = 'menu';
        },

        // ===========================================
        // 3. ТРЕНИРОВКА И ИИ
        // ===========================================

        // Открыть каталог задач
        async openCatalog() {
            try {
                this.trainingTasks = await Api.getTrainingTasks(this.token, this.subject);
                this.state = 'catalog';
            } catch(e) { alert("Не удалось загрузить каталог"); }
        },

        // Открыть задачу из каталога вручную
        openTaskManual(t) {
            this.activeTask = t;
            // В каталоге подсказки недоступны (или можно сделать отдельный запрос)
            this.activeTask.hints_available = 0;
            this.trainingAnswer = '';
            this.solveResult = null;
            this.revealedHints = [];
            this.state = 'training_solve';
        },

        // Экран выбора темы
        openTopicSelection() {
            this.state = 'topic_select';
        },

        // Генерация задачи ИИ
        async selectTopic(topicId) {
            this.state = 'loading_ai';
            try {
                // Передаем токен, предмет, тему и выбранную сложность
                this.activeTask = await Api.generateAiTask(
                    this.token,
                    this.subject,
                    topicId,
                    this.selectedDifficulty
                );

                // Сброс полей
                this.trainingAnswer = '';
                this.solveResult = null;
                this.revealedHints = [];

                this.state = 'training_solve';

            } catch (e) {
                alert(e.message);
                this.state = 'topic_select';
            }
        },

        // Отправка ответа (тренировка)
        async submitTrainingAnswer(ans = null) {
            const val = ans !== null ? ans : this.trainingAnswer;
            if (!val) return;

            try {
                const res = await Api.solveTask(this.token, this.activeTask.id, val);
                this.solveResult = res.status;
                if (res.status === 'correct') {
                    this.fetchStats(); // Обновляем опыт
                    this.activeTask.is_solved = true;
                }
            } catch(e) { alert("Ошибка соединения"); }
        },

        // Взять подсказку
        async useHint() {
            if (this.revealedHints.length >= this.activeTask.hints_available) return;

            this.isHintLoading = true;
            try {
                const num = this.revealedHints.length + 1;
                const d = await Api.getHint(this.token, this.activeTask.id, num);
                this.revealedHints.push(d.hint_text);
            } catch(e) { alert("Не удалось получить подсказку"); }
            finally { this.isHintLoading = false; }
        },

        // ===========================================
        // 4. PVP (СОКЕТЫ)
        // ===========================================
        startSearch() {
            if (!this.subject) return alert("Выберите предмет");

            this.state = 'searching';
            this.myScore = 0;
            this.enemyScore = 0;

            if (this.ws) this.ws.close();

            const proto = location.protocol === 'https:' ? 'wss' : 'ws';
            const url = `${proto}://${location.host}/ws/pvp?subject=${this.subject}&token=${this.token}`;

            this.ws = new WebSocket(url);

            this.ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                this.handleSocketMessage(d);
            };

            this.ws.onerror = () => {
                alert("Ошибка подключения к серверу соревнований");
                this.reset();
            };
        },

        handleSocketMessage(d) {
            switch(d.type) {
                case 'match_found': this.handleMatchFound(d); break;
                case 'round_start': this.startRound(d); break;
                case 'pressure_timer': this.handlePressure(d); break;
                case 'round_result': this.showRoundResult(d); break;
                case 'game_over': this.endGame(d); break;
                case 'error': alert(d.message); this.reset(); break;
            }
        },

        handleMatchFound(d) {
            this.state = 'vs';
            this.opponentName = d.opponent;
            this.opponentRating = d.rating;
            this.vsTimer = d.time || 5;

            if(this.intervals.vs) clearInterval(this.intervals.vs);
            this.intervals.vs = setInterval(() => {
                if(this.vsTimer > 0) this.vsTimer--;
            }, 1000);
        },

        startRound(d) {
            this.clearTimers();
            this.state = 'playing';
            this.roundFinished = false;
            this.answerSent = false;
            this.answer = '';

            // Сохраняем данные задачи
            this.task = {
                title: d.title,
                desc: d.desc,
                difficulty: d.difficulty,
                task_type: d.task_type,
                options: d.options
            };

            this.currentRound = d.round;
            this.totalRounds = d.total;
            this.timeLeft = '∞'; // Изначально времени нет (ждем первого ответа)

            // Ставим фокус в поле
            setTimeout(() => document.getElementById('pvpInput')?.focus(), 50);

        },

        handlePressure(d) {
            // Включаем таймер, когда соперник ответил
            this.timeLeft = d.seconds;

            if (this.intervals.game) clearInterval(this.intervals.game);
            this.intervals.game = setInterval(() => {
                if(typeof this.timeLeft === 'number' && this.timeLeft > 0) {
                    this.timeLeft--;
                }
            }, 1000);
        },

        sendPvPAnswer() {
            if(!this.answer || this.answerSent) return;
            this.ws.send(JSON.stringify({answer: this.answer}));
            this.answerSent = true;
        },

        showRoundResult(d) {
            this.roundFinished = true;
            this.roundResult = { you: d.you, enemy: d.enemy, correct: d.correct_answer };

            if(d.you === 'correct') this.myScore++;
            if(d.enemy === 'correct') this.enemyScore++;

            this.nextRoundTimer = 4;
            this.intervals.next = setInterval(() => {
                if(this.nextRoundTimer > 0) this.nextRoundTimer -= 0.1;
            }, 100);

        },

        endGame(d) {
            this.clearTimers();
            this.state = 'finished';
            this.finalData = d;
            this.fetchStats(); // Обновляем рейтинг
        },

        // ===========================================
        // 5. ИСТОРИЯ И АНАЛИТИКА
        // ===========================================
        async openHistory() {
            try {
                this.historyList = await Api.getHistory(this.token);
                this.showHistory = true;
            } catch { alert("Не удалось загрузить историю"); }
        },
        async openAnalytics() {
            try {
                this.analyticsData = await Api.getAnalytics(this.token);
                this.showAnalytics = true;
            } catch { alert("Не удалось загрузить аналитику"); }
        },

        // Хелперы для стилизации истории
        getMatchClass(m) {
            if (m.winner && m.winner.username === this.userStats.username) return 'h-win';
            if (m.loser && m.loser.username === this.userStats.username) return 'h-lose';
            return 'h-draw';
        },
        getResultText(m) {
            if (m.winner && m.winner.username === this.userStats.username) return 'ПОБЕДА';
            if (m.loser && m.loser.username === this.userStats.username) return 'ПОРАЖЕНИЕ';
            return 'НИЧЬЯ';
        }
    }
}).mount('#app');