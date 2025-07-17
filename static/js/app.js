// Initialize Socket.IO connection
const socket = io();

// State
let totalEvents = 0;
let activeSymbols = ['BTC', 'ETH'];
let thresholds = {
    minLiquidation: 100000,
    minTrade: 500000
};

// Symbol mapping
const symbolMap = {
    'btc': 'BTC',
    'eth': 'ETH',
    'sol': 'SOL',
    'bnb': 'BNB',
    'doge': 'DOGE',
    'xrp': 'XRP',
    'ada': 'ADA',
    'avax': 'AVAX'
};

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('liquidation', (event) => {
    addLiquidation(event.data);
    updateTotalEvents();
});

socket.on('trade', (event) => {
    addTrade(event.data);
    updateTotalEvents();
});

socket.on('funding', (data) => {
    updateFundingRate(data.symbol, data.data);
});

// Setup controls
document.addEventListener('DOMContentLoaded', () => {
    // Initialize funding cards for default symbols
    updateFundingCards();
    
    // Apply settings button
    document.getElementById('apply-settings').addEventListener('click', applySettings);
    
    // Send initial settings to server
    sendSettingsUpdate();
});

// Functions
function addLiquidation(data) {
    // Filter by active symbols
    if (!activeSymbols.includes(data.symbol)) return;
    
    // Filter by threshold
    if (data.usdValue < thresholds.minLiquidation) return;
    
    const list = document.getElementById('liquidations-list');
    const item = document.createElement('div');
    
    const isLong = data.side === 'SELL';
    item.className = `event-item ${isLong ? 'liquidation-long' : 'liquidation-short'}`;
    
    const largeClass = data.usdValue >= 1000000 ? 'large-value' : '';
    
    item.innerHTML = `
        <div class="time">${new Date(data.timestamp).toLocaleTimeString()}</div>
        <div>
            <span class="symbol">${data.symbol}</span>
            <span class="type">${isLong ? 'LONG LIQ' : 'SHORT LIQ'}</span>
            <span class="price">@ $${data.price.toLocaleString()}</span>
            <span class="value ${largeClass}">$${formatValue(data.usdValue)}</span>
        </div>
    `;
    
    list.insertBefore(item, list.firstChild);
    
    // Keep only last 50 items
    while (list.children.length > 50) {
        list.removeChild(list.lastChild);
    }
}

function addTrade(data) {
    // Filter by active symbols
    if (!activeSymbols.includes(data.symbol)) return;
    
    // Filter by threshold
    if (data.usdValue < thresholds.minTrade) return;
    
    const list = document.getElementById('trades-list');
    const item = document.createElement('div');
    
    const isBuy = data.direction === 'BUY';
    item.className = `event-item ${isBuy ? 'trade-buy' : 'trade-sell'}`;
    
    const largeClass = data.usdValue >= 3000000 ? 'large-value' : '';
    
    item.innerHTML = `
        <div class="time">${data.timestr}</div>
        <div>
            <span class="symbol">${data.symbol}</span>
            <span class="type">${data.direction}</span>
            <span class="value ${largeClass}">$${formatValue(data.usdValue)}</span>
        </div>
    `;
    
    list.insertBefore(item, list.firstChild);
    
    // Keep only last 50 items
    while (list.children.length > 50) {
        list.removeChild(list.lastChild);
    }
}

function updateFundingRate(symbol, data) {
    const symbolShort = symbol.replace('USDT', '');
    
    // Check if this symbol is active
    if (!activeSymbols.includes(symbolShort)) return;
    
    const elementId = `${symbolShort.toLowerCase()}-funding`;
    const card = document.getElementById(elementId);
    
    if (!card) return;
    
    // Update values
    card.querySelector('.rate').textContent = `${data.rate > 0 ? '+' : ''}${data.rate.toFixed(4)}%`;
    card.querySelector('.annual').textContent = `Annual: ${data.annual > 0 ? '+' : ''}${data.annual.toFixed(1)}%`;
    card.querySelector('.direction').textContent = data.direction;
    
    // Update styling
    card.className = 'funding-card';
    if (data.rate > 0) {
        card.classList.add('positive');
    } else if (data.rate < 0) {
        card.classList.add('negative');
    }
    
    if (Math.abs(data.annual) > 50) {
        card.classList.add('extreme');
    }
}

function updateTotalEvents() {
    totalEvents++;
    // Total events counter removed from UI
}

function formatValue(value) {
    if (value >= 1000000) {
        return (value / 1000000).toFixed(2) + 'M';
    } else if (value >= 1000) {
        return (value / 1000).toFixed(0) + 'K';
    }
    return value.toFixed(0);
}

function applySettings() {
    // Get selected symbols
    const newSymbols = [];
    Object.keys(symbolMap).forEach(key => {
        const checkbox = document.getElementById(`${key}-check`);
        if (checkbox && checkbox.checked) {
            newSymbols.push(symbolMap[key]);
        }
    });
    
    // Get thresholds
    const newMinLiquidation = parseInt(document.getElementById('min-liquidation').value) || 0;
    const newMinTrade = parseInt(document.getElementById('min-trade').value) || 0;
    
    // Update state
    activeSymbols = newSymbols;
    thresholds.minLiquidation = newMinLiquidation;
    thresholds.minTrade = newMinTrade;
    
    // Update funding cards
    updateFundingCards();
    
    // Send to server
    sendSettingsUpdate();
    
    // Visual feedback
    const btn = document.getElementById('apply-settings');
    btn.textContent = 'Applied!';
    btn.style.background = '#1a7f37';
    setTimeout(() => {
        btn.textContent = 'Apply Settings';
        btn.style.background = '#238636';
    }, 1500);
}

function updateFundingCards() {
    const container = document.getElementById('funding-rates');
    container.innerHTML = '';
    
    activeSymbols.forEach(symbol => {
        const card = document.createElement('div');
        card.className = 'funding-card';
        card.id = `${symbol.toLowerCase()}-funding`;
        card.innerHTML = `
            <h3>${symbol}/USDT</h3>
            <div class="rate">--</div>
            <div class="annual">Annual: --</div>
            <div class="direction">--</div>
        `;
        container.appendChild(card);
    });
}

function sendSettingsUpdate() {
    socket.emit('update_settings', {
        symbols: activeSymbols,
        minLiquidation: thresholds.minLiquidation,
        minTrade: thresholds.minTrade
    });
}