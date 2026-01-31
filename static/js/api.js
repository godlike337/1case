// api.js
const API_PREFIX = '';

function getHeaders(token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

export async function loginUser(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_PREFIX}/token`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error("Login failed");
    return await res.json();
}

export async function registerUser(form) {
    const res = await fetch(`${API_PREFIX}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
    });
    if (!res.ok) throw new Error("Registration failed");
    return await res.json();
}

export async function getUserStats(token) {
    const res = await fetch(`${API_PREFIX}/users/me`, { headers: getHeaders(token) });
    return await res.json();
}

export async function getHistory(token) {
    const res = await fetch(`${API_PREFIX}/users/me/history`, { headers: getHeaders(token) });
    return await res.json();
}

export async function getAnalytics(token) {
    const res = await fetch(`${API_PREFIX}/analytics/me`, { headers: getHeaders(token) });
    return await res.json();
}

export async function generateAiTask(token, subject, grade, topic, difficulty) {
    const res = await fetch(`${API_PREFIX}/tasks/training/generate`, {
        method: 'POST',
        headers: getHeaders(token),
        body: JSON.stringify({ subject, grade, topic, difficulty })
    });
    if (!res.ok) throw new Error("AI Generation failed");
    return await res.json();
}

export async function solveTask(token, taskId, answer) {
    const res = await fetch(`${API_PREFIX}/tasks/${taskId}/solve`, {
        method: 'POST',
        headers: getHeaders(token),
        body: JSON.stringify({ user_answer: answer })
    });
    return await res.json();
}

export async function getHint(token, taskId, num) {
    const res = await fetch(`${API_PREFIX}/tasks/${taskId}/hint?hint_number=${num}`, { headers: getHeaders(token) });
    return await res.json();
}