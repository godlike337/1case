// Вспомогательная функция для заголовков
function getHeaders(token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

export async function loginUser(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('/token', { method: 'POST', body: formData });
    if (!res.ok) throw new Error("Ошибка входа");
    return await res.json();
}

export async function registerUser(form) {
    const res = await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
    });
    if (!res.ok) throw new Error("Ошибка регистрации");
    return await res.json();
}

export async function getUserStats(token) {
    const res = await fetch('/users/me', { headers: getHeaders(token) });
    if (!res.ok) throw new Error("Ошибка загрузки профиля");
    return await res.json();
}

export async function getHistory(token) {
    const res = await fetch('/users/me/history', { headers: getHeaders(token) });
    if (!res.ok) throw new Error("Ошибка загрузки истории");
    return await res.json();
}

export async function getTrainingTasks(token, subject) {
    const res = await fetch(`/tasks/?subject=${subject}`, { headers: getHeaders(token) });
    if (!res.ok) throw new Error("Ошибка загрузки задач");
    return await res.json();
}

export async function solveTask(token, taskId, answer) {
    const res = await fetch(`/tasks/${taskId}/solve`, {
        method: 'POST',
        headers: getHeaders(token),
        body: JSON.stringify({ user_answer: answer })
    });
    if (!res.ok) throw new Error("Ошибка проверки");
    return await res.json();
}