// ✅ Check connection
console.log("✅ GreenTrack script connected successfully!");

// --- 页面加载动画 ---
window.onload = function () {
  const title = document.querySelector(".hero h1");
  if (title) {
    title.style.transition = "all 1s ease";
    title.style.transform = "scale(1.1)";
    setTimeout(() => (title.style.transform = "scale(1)"), 1000);
  }
};

// --- 初始化账户数据 ---
let accounts = JSON.parse(localStorage.getItem("accounts")) || {

    user: [
        { username: "GreenUser01", password: "User#1234" },
        { username: "EcoCitizen", password: "Recycle#2024" },
        { username: "SibuResident", password: "Sibu#5678" }
    ],

    merchant: [
        { username: "MerchantSibu", password: "Merchant#888" }
    ],

    officer: [
        { username: "OfficerSMC", password: "Admin#1234" },
        { username: "WasteDept", password: "Green#2025" }
    ],

    superadmin: [
        { username: "SuperAdmin", password: "Master#2025" }
    ]

};

// --- 打开角色登录面板 ---
function openRole(role) {
  const roleButtons = document.querySelector(".role-buttons");
  roleButtons.style.display = "none";
  document.querySelectorAll(".role-panel").forEach(p => p.classList.add("hidden"));
  document.getElementById(role + "-panel").classList.remove("hidden");
  document.body.className = ""; // 重置背景

  // 根据角色切换背景颜色
  if (role === "user") document.body.style.backgroundColor = "#e0f7fa";
  if (role === "merchant") document.body.style.backgroundColor = "#fff9c4";
  if (role === "officer") document.body.style.backgroundColor = "#ffe0b2";
}

// --- 返回角色选择 ---
function goBack() {
  document.querySelectorAll(".role-panel").forEach(p => p.classList.add("hidden"));
  const roleButtons = document.querySelector(".role-buttons");
  roleButtons.style.display = "block";
  document.body.style.backgroundColor = "#ffffff";
}

// --- 切换密码显示/隐藏 👁️ ---
function togglePassword(id, icon) {
  const input = document.getElementById(id);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    icon.textContent = "🙈";
  } else {
    input.type = "password";
    icon.textContent = "👁️";
  }
}

// --- 注册新用户 ---
function showRegister(role) {
  if (role !== "user") {
    alert("⚠️ Only regular users can register. Please contact admin.");
    return;
  }

  const name = prompt("Enter new username:");
  const pass = prompt("Enter new password:");
  if (!name || !pass) return;

  if (accounts.user.some(u => u.username === name)) {
    alert("❌ Username already exists!");
    return;
  }

  const nameRule = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}$/;
  const passRule = /^(?=.*[A-Z])(?=.*\\d)(?=.*[!@#$%^&*+\\-?]).{8,}$/;
  if (!nameRule.test(name)) return alert("❌ Username must have 8+ chars with A-Z, a-z, number.");
  if (!passRule.test(pass)) return alert("❌ Password must include uppercase, number, symbol.");

  accounts.user.push({ username: name, password: pass });
  localStorage.setItem("accounts", JSON.stringify(accounts));
  alert("✅ Registration successful!");
}

// --- 登录逻辑 ---
function loginUser(e, role) {
  e.preventDefault();
  const name = document.getElementById(role + "-username").value.trim();
  const pass = document.getElementById(role + "-password").value.trim();
  const msg = document.getElementById(role + "-msg");
  msg.textContent = "";

  const found = accounts[role]?.find(u => u.username === name && u.password === pass);
  const superFound = accounts.superadmin.find(u => u.username === name && u.password === pass);

  if (superFound) {
    msg.style.color = "green";
    msg.textContent = "👑 SuperAdmin access granted!";
    setTimeout(() => (window.location.href = "admin_dashboard.html"), 1000);
    return;
  }

  if (found) {
    msg.style.color = "green";
    msg.textContent = "✅ Login successful! Redirecting...";
    localStorage.setItem("currentUser", name);
    setTimeout(() => {
      if (role === "user") window.location.href = "user_dashboard.html";
      if (role === "merchant") window.location.href = "merchant_dashboard.html";
      if (role === "officer") window.location.href = "officer_dashboard.html";
    }, 1000);
  } else {
    msg.style.color = "red";
    msg.textContent = "❌ Invalid username or password.";
  }
}

// ✅ GreenTrack script connected
console.log("✅ GreenTrack system running...");

// --- 页面载入动画 ---
window.onload = function () {
  const title = document.querySelector(".hero h1");
  if (title) {
    title.style.transition = "all 1s ease";
    title.style.transform = "scale(1.1)";
    setTimeout(() => (title.style.transform = "scale(1)"), 1000);
  }
};

// --- 初始化账户（含测试账号） ---
let accounts = JSON.parse(localStorage.getItem("accounts")) || {
  user: [
    { username: "GreenUser01", password: "User#1234" },
    { username: "EcoCitizen", password: "Recycle#2025" },
    { username: "SibuResident", password: "Green#8888" },
  ],
  merchant: [{ username: "MerchantSibu", password: "Recycle#5678" }],
  officer: [
    { username: "OfficerSMC", password: "Admin#1234" },
    { username: "WasteDept", password: "Green#2025" },
  ],
  superadmin: [{ username: "SuperAdmin", password: "Master#2025" }],
};

// --- 打开角色登录 ---
function openRole(role) {
  document.querySelectorAll(".role-panel").forEach((p) => p.classList.remove("active"));
  const panel = document.getElementById(role + "-panel");
  if (panel) {
    panel.classList.add("active");
    panel.scrollIntoView({ behavior: "smooth" });
  }
}

// --- 注册新用户（仅 user）---
function showRegister(role) {
  if (role !== "user") {
    alert("⚠️ Only regular users can register. Please contact system admin.");
    return;
  }

  const username = prompt("Enter new username:");
  const password = prompt("Enter new password:");
  if (!username || !password) return;

  if (accounts[role].some((u) => u.username === username)) {
    alert("❌ Username already exists!");
    return;
  }

  const nameRule = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
  const passRule = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*+\-?]).{8,}$/;
  if (!nameRule.test(username)) {
    alert("❌ Username must include A-Z, a-z, number and ≥8 chars.");
    return;
  }
  if (!passRule.test(password)) {
    alert("❌ Password must have uppercase, number and symbol.");
    return;
  }

  accounts[role].push({ username, password });
  localStorage.setItem("accounts", JSON.stringify(accounts));
  alert(`✅ ${role.toUpperCase()} registered successfully!`);
}

// --- 登录用户 ---
function loginUser(e, role) {
  e.preventDefault();
  const name = document.getElementById(role + "-username").value.trim();
  const pass = document.getElementById(role + "-password").value.trim();
  const msg = document.getElementById(role + "-msg");

  const found = accounts[role]?.find((u) => u.username === name && u.password === pass);

  if (found) {
    msg.style.color = "green";
    msg.textContent = "✅ Login successful! Redirecting...";

    // 将当前用户保存到 localStorage
    localStorage.setItem("currentUser", JSON.stringify({ role, username: name }));

    setTimeout(() => {
      if (role === "user") window.location.href = "user_dashboard.html";
      if (role === "merchant") window.location.href = "merchant_dashboard.html";
      if (role === "officer") window.location.href = "officer_dashboard.html";
      if (role === "superadmin") window.location.href = "admin_dashboard.html";
    }, 800);
  } else {
    msg.style.color = "red";
    msg.textContent = "❌ Invalid username or password.";
  }
}

// --- 登出 ---
function logout() {
  localStorage.removeItem("currentUser");
  window.location.href = "index.html";
}

// --- 用户仪表板数据渲染（for user_dashboard.html）---
function loadUserDashboard() {
  const user = JSON.parse(localStorage.getItem("currentUser"));
  if (!user || user.role !== "user") {
    window.location.href = "index.html";
    return;
  }

  // 设置用户名显示
  document.getElementById("user-name").innerText = user.username;

  // 示例假数据
  document.getElementById("event-list").innerHTML = `
    <tr><td>Sibu Green Day</td><td>2025-03-10</td><td>9:00 AM</td><td>✔ Participated</td></tr>
    <tr><td>School Recycling Week</td><td>2025-04-05</td><td>8:00 AM</td><td>✔ Participated</td></tr>
  `;

  document.getElementById("recycling-list").innerHTML = `
    <tr><td>2025-03-02</td><td>Plastic Bottles</td><td>3.5</td><td>2.50</td><td>8.75</td></tr>
    <tr><td>2025-03-12</td><td>Old Newspaper</td><td>4.0</td><td>0.20</td><td>0.80</td></tr>
  `;

  document.getElementById("points").innerText = "120";
  document.getElementById("rank").innerText = "#5 in Sibu";

  // Chart.js 图表
  const ctx = document.getElementById("recycleChart");
  if (ctx) {
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["Jan", "Feb", "Mar", "Apr"],
        datasets: [{
          label: "Recycled (kg)",
          data: [8, 12, 15, 10],
          backgroundColor: "rgba(46, 125, 50, 0.7)",
        }],
      },
    });
  }
}
