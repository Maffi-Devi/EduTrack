function setChatOpen(open){
    const widget = document.getElementById('chatWidget');
    widget.classList.toggle('open', open);
    document.getElementById('chatToggle').textContent = open ? '▼' : '▲';
    if(open) document.getElementById('chatInput').focus();
}

function toggleChat(){
    setChatOpen(!document.getElementById('chatWidget').classList.contains('open'));
}

// Close the chat when clicking anywhere outside it
document.addEventListener('click', function(e){
    const widget = document.getElementById('chatWidget');
    if(widget && widget.classList.contains('open') && !widget.contains(e.target)){
        setChatOpen(false);
    }
});

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
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({message: msg})
        });
        if(!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        const typing = document.getElementById('typing-indicator');
        if(typing) typing.remove();
        msgs.innerHTML += `<div class="bot-msg">${escapeHtml(data.reply).replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<b>$1</b>')}</div>`;
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
