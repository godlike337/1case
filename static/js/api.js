function getHeaders(token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}
export async function loginUser(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username); formData.append('password', password);
    const res = await fetch('/token', { method: 'POST', body: formData });
    if (!res.ok) throw new Error("Ошибка"); return await res.json();
}
export async function registerUser(form) {
    const res = await fetch('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
    if (!res.ok) throw new Error("Ошибка"); return await res.json();
}
export async function getUserStats(token) {
    const res = await fetch('/users/me', { headers: getHeaders(token) });
    return await res.json();
}
export async function getHistory(token) {
    const res = await fetch('/users/me/history', { headers: getHeaders(token) });
    return await res.json();
}
export async function getAnalytics(token) {
    const res = await fetch('/analytics/me', { headers: getHeaders(token) });
    if (!res.ok) throw new Error(); return await res.json();
}
export async function generateAiTask(token, subject, topic, difficulty) {
    const res = await fetch('/tasks/training/generate', {
        method: 'POST', headers: getHeaders(token), body: JSON.stringify({ subject, topic, difficulty })
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
    return await res.json();
}
export async function solveTask(token, taskId, answer) {
    const res = await fetch(`/tasks/${taskId}/solve`, { method: 'POST', headers: getHeaders(token), body: JSON.stringify({ user_answer: answer }) });
    if (!res.ok) throw new Error(); return await res.json();
}
export async function getHint(token, taskId, num) {
    const res = await fetch(`/tasks/${taskId}/hint?hint_number=${num}`, { headers: getHeaders(token) });
    if (!res.ok) throw new Error(); return await res.json();
}
export async function getTrainingTasks(token, subject) {
    const res = await fetch(`/tasks/?subject=${subject}`, { headers: getHeaders(token) });
    if (!res.ok) throw new Error(); return await res.json();
}