function toggleChat(){
    const body = document.getElementById('chatBody');
    const tog  = document.getElementById('chatToggle');
    if(body.style.display === 'none'){
        body.style.display = 'flex';
        tog.textContent = '▼';
    } else {
        body.style.display = 'none';
        tog.textContent = '▲';
    }
}

async function sendMsg(){
    const input = document.getElementById('chatInput');
    const msgs  = document.getElementById('chatMessages');
    const msg   = input.value.trim();
    if(!msg) return;
    msgs.innerHTML += `<div class="user-msg">${escapeHtml(msg)}</div>`;
    msgs.innerHTML += `<div class="bot-msg typing" id="typing-indicator">EduBot is thinking... 💭</div>`;
    msgs.scrollTop = msgs.scrollHeight;
    input.value = '';
    input.disabled = true;
    try {
        const res  = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
        });
        const data = await res.json();
        const typing = document.getElementById('typing-indicator');
        if(typing) typing.remove();
        msgs.innerHTML += `<div class="bot-msg">${data.reply.replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<b>$1</b>')}</div>`;
    } catch(e) {
        const typing = document.getElementById('typing-indicator');
        if(typing) typing.textContent = '❌ Connection error. Please try again.';
    }
    input.disabled = false;
    input.focus();
    msgs.scrollTop = msgs.scrollHeight;
}

function escapeHtml(text){
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
