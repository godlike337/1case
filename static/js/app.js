// Импорт Vue.js через ES Module (для работы import/export)
import { createApp } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';
import * as Api from './api.js';

createApp({
    data() {
        return {
            token: localStorage.getItem('olymp_token') || null,
            authForm: { username: '', password: '', email: '' },
            userStats: {},
            state: 'menu',
            subject: 'python',

            // PvP Data
            ws: null, task: {}, answer: '', answerSent: false, timeLeft: 0,
            currentRound: 1, totalRounds: 3, myScore: 0, enemyScore: 0,
            roundFinished: false, roundResult: {}, nextRoundTimer: 0,
            gameTimer: null, nextRoundInterval: null, finalData: {},

            // Training Data
            trainingTasks: [], activeTask: {}, trainingAnswer: '', solveResult: null,

            // History
            showHistory: false, historyList: [], currentUser: ''
        }
    },
    mounted() { if (this.token) this.fetchStats(); },
    methods: {
        // --- AUTH ---
        async fetchStats() {
            try {
                this.userStats = await Api.getUserStats(this.token);
                this.currentUser = this.userStats.username;
            } catch (e) { this.logout(); }
        },
        async login() {
            try {
                const data = await Api.loginUser(this.authForm.username, this.authForm.password);
                this.token = data.access_token;
                localStorage.setItem('olymp_token', this.token);
                this.fetchStats();
            } catch (e) { alert(e.message); }
        },
        async register() {
            try {
                await Api.registerUser(this.authForm);
                await this.login();
            } catch (e) { alert(e.message); }
        },
        logout() {
            this.token = null; localStorage.removeItem('olymp_token'); this.state = 'menu';
        },

        // --- PVP ---
        startSearch() {
            this.state = 'searching';
            const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
            this.ws = new WebSocket(`${protocol}://${location.host}/ws/pvp?subject=${this.subject}&token=${this.token}`);
            this.ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'round_start') this.startRound(data);
                else if (data.type === 'round_result') this.showPvPResult(data);
                else if (data.type === 'game_over') this.endGame(data);
                else if (data.type === 'error') { alert(data.message); this.reset(); }
            };
            this.ws.onclose = () => { if(this.state === 'searching') this.reset(); };
        },
        startRound(data) {
            clearInterval(this.nextRoundInterval); this.nextRoundTimer = 0;
            this.state = 'playing'; this.roundFinished = false; this.answerSent = false; this.answer = '';
            this.task = { title: data.title, desc: data.desc };
            this.currentRound = data.round; this.totalRounds = data.total;
            setTimeout(() => document.getElementById('pvpInput')?.focus(), 100);
            this.timeLeft = data.time;
            if(this.gameTimer) clearInterval(this.gameTimer);
            this.gameTimer = setInterval(() => { if(this.timeLeft > 0) this.timeLeft--; }, 1000);
        },
        sendPvPAnswer() {
            if(!this.answer || this.answerSent) return;
            this.ws.send(JSON.stringify({answer: this.answer}));
            this.answerSent = true;
        },
        showPvPResult(data) {
            this.roundFinished = true;
            this.roundResult = { you: data.you, enemy: data.enemy, correct: data.correct_answer };
            if(data.you === 'correct') this.myScore++;
            if(data.enemy === 'correct') this.enemyScore++;
            this.nextRoundTimer = 4;
            if(this.nextRoundInterval) clearInterval(this.nextRoundInterval);
            this.nextRoundInterval = setInterval(() => { if(this.nextRoundTimer > 0) this.nextRoundTimer -= 0.1; }, 100);
        },
        endGame(data) {
            clearInterval(this.gameTimer); clearInterval(this.nextRoundInterval);
            this.state = 'finished'; this.finalData = data;
            this.fetchStats();
        },
        reset() { if(this.ws) this.ws.close(); this.state = 'menu'; this.myScore = 0; this.enemyScore = 0; },

        // --- TRAINING ---
        async openTraining() {
            try {
                this.trainingTasks = await Api.getTrainingTasks(this.token, this.subject);
                this.state = 'training_list';
            } catch (e) { alert(e.message); }
        },
        openTask(t) { this.activeTask = t; this.trainingAnswer = ''; this.solveResult = null; this.state = 'training_solve'; },
        async checkTrainingAnswer() {
            if(!this.trainingAnswer) return;
            try {
                const data = await Api.solveTask(this.token, this.activeTask.id, this.trainingAnswer);
                this.solveResult = data.status;
                if(data.status === 'correct') this.fetchStats();
            } catch (e) { alert(e.message); }
        },

        // --- HISTORY ---
        async openHistory() {
            try {
                this.historyList = await Api.getHistory(this.token);
                this.showHistory = true;
            } catch (e) { alert(e.message); }
        },
        isWin(m) { return m.winner && m.winner.username === this.currentUser; },
        isLose(m) { return m.loser && m.loser.username === this.currentUser; },
        getMatchClass(m) { return this.isWin(m) ? 'h-win' : (this.isLose(m) ? 'h-lose' : 'h-draw'); },
        getResultText(m) { return this.isWin(m) ? 'ПОБЕДА' : (this.isLose(m) ? 'ПОРАЖЕНИЕ' : 'НИЧЬЯ'); },
        getScoreText(m) { return `${m.winner_score} : ${m.loser_score}`; }
    }
}).mount('#app');