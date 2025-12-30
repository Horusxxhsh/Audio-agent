# Polymarket 抢跑交易实时监控系统设计文档

**日期**: 2025-12-30
**版本**: 1.0
**作者**: AI Design Assistant

---

## 1. 概述

### 1.1 项目目标

构建一个实时监控系统，自动检测 Polymarket 预测市场平台上的**抢跑交易（Front-running）**行为。抢跑交易是指攻击者在得知大额交易即将执行时，利用信息优势提前下单，在大额交易推动价格变化后反向操作获利。

### 1.2 核心需求

- **实时监控**: 毫秒级检测可疑交易行为
- **智能分析**: 结合传统算法和 LLM 进行多维度分析
- **自动告警**: 分级告警机制，多渠道推送
- **可扩展性**: 支持水平扩展，应对高并发交易场景

### 1.3 参考依据

- 哥伦比亚大学 2025 年研究显示 Polymarket 约 25% 交易量为虚假交易[^1]
- 区块链透明性使得交易 forensic analysis 成为可能[^2]

---

## 2. 系统架构

### 2.1 架构概览

系统采用 **Node.js + Python 混合架构 + LLM 增强分析**，分为四个主要层：

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部数据源                                │
│  Polymarket CLOB API │ Polymarket Data API │ Polygon RPC       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    实时数据采集层 (Node.js)                      │
│  - WebSocket 连接管理                                           │
│  - 交易流订阅                                                   │
│  - Mempool 监控                                                 │
│  - 网络自动检测                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据缓存层 (Redis)                          │
│  - 交易流队列 (Redis Stream)                                    │
│  - 订单簿状态缓存                                               │
│  - 钱包行为模式缓存                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              分析引擎层 (Python + LLM)                           │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  传统算法检测    │    │   LLM 智能分析   │                   │
│  │  - Mempool分析   │    │  - 行为解释      │                   │
│  │  - 交易序列分析  │    │  - 风险评估      │                   │
│  │  - 关联账户检测  │    │  - 告警生成      │                   │
│  └──────────────────┘    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   告警与存储层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │   WebSocket  │  │  告警渠道    │         │
│  │  历史数据    │  │  实时推送    │  │  邮件/Slack  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

| 层级 | 技术选择 | 理由 |
|------|----------|------|
| 实时采集 | Node.js + ws | 擅长处理并发连接和实时数据流 |
| 数据缓存 | Redis Stream | 高性能消息队列，支持流式处理 |
| 分析引擎 | Python | 丰富的数据科学和机器学习库 |
| LLM 集成 | OpenAI API / Claude API | 强大的自然语言理解能力 |
| 数据存储 | PostgreSQL + TimescaleDB | 时序数据优化，支持复杂查询 |
| 前端展示 | React + WebSocket | 实时仪表板展示 |

---

## 3. 数据流设计

### 3.1 统一数据格式

**交易事件格式:**
```json
{
  "event_type": "trade" | "order_pending" | "order_filled",
  "timestamp": "2025-12-30T10:00:00.123Z",
  "block_number": 12345678,
  "tx_hash": "0xabc123...",
  "market_id": "polymarket-market-123",
  "token": "outcome-token-yes",
  "maker": "0x_maker_addr",
  "taker": "0x_taker_addr",
  "side": "buy" | "sell",
  "price": 0.65,
  "size": 1000,
  "size_usd": 650.00,
  "gas_price": 50000000000,
  "source": "clob" | "mempool" | "onchain"
}
```

### 3.2 数据流处理流程

```
[数据源] → [Node.js 采集] → [Redis Stream] → [Python 分析] → [存储/告警]
```

#### 步骤 1: 数据采集 (Node.js)

```javascript
// 自动检测 Polymarket 所在区块链
async function detectNetwork() {
  const networks = [
    { chainId: 137, name: 'Polygon', rpc: 'https://polygon-rpc.com' },
    { chainId: 1, name: 'Ethereum', rpc: 'https://eth.llamarpc.com' }
  ];
  // 通过测试交易验证
  for (const network of networks) {
    try {
      const provider = new ethers.JsonRpcProvider(network.rpc);
      const code = await provider.getCode(POLYMARKET_CONTRACT);
      if (code !== '0x') return network;
    } catch (e) { continue; }
  }
}

// WebSocket 订阅交易流
async function subscribeToTrades() {
  const ws = new WebSocket(POLYMARKET_CLOB_WS);
  ws.on('message', (data) => {
    const trade = normalizeTrade(data);
    redis.xAdd('transactions:stream', '*', trade);
  });
}
```

#### 步骤 2: 缓存与排队 (Redis)

```python
# Redis Stream 配置
STREAM_KEY = 'transactions:stream'
CONSUMER_GROUP = 'analyzers'
TTL_SECONDS = 86400  # 保留24小时

# 写入交易
await redis.xadd(
    STREAM_KEY,
    {'event': json.dumps(trade_event)},
    maxlen=100000  # 最多保留10万条
)
```

#### 步骤 3: 批量消费 (Python)

```python
async def consume_transactions():
    while True:
        events = await redis.xreadgroup(
            CONSUMER_GROUP,
            'consumer-1',
            {STREAM_KEY: '>'},
            count=50,
            block=100
        )
        for stream, messages in events:
            for message_id, data in messages:
                event = json.loads(data[b'event'])
                await analyze_transaction(event)
                await redis.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
```

---

## 4. 抢跑检测算法

### 4.1 检测模式 A: Mempool 抢跑

**原理**: 检测攻击者监控 Mempool，在大额交易确认前抢先交易。

**检测逻辑**:
```python
class MempoolFrontRunDetector:
    def __init__(self):
        self.pending_txs = {}  # 交易哈希 -> 待处理交易
        self.window_seconds = 2

    async def process(self, event: TradeEvent):
        # 1. 记录待处理交易
        if event.source == 'mempool':
            self.pending_txs[event.tx_hash] = event

        # 2. 检测已确认交易是否被抢跑
        if event.source == 'onchain' and event.size_usd > 10000:
            await self.check_front_running(event)

    async def check_front_running(self, large_tx: TradeEvent):
        # 检测2秒内同市场的反向小额交易
        suspicious = []
        for tx_hash, pending in self.pending_txs.items():
            if (pending.market_id == large_tx.market_id and
                pending.side != large_tx.side and
                abs(pending.timestamp - large_tx.timestamp) < self.window_seconds and
                pending.size_usd < large_tx.size_usd * 0.1):
                suspicious.append(pending)

        if suspicious:
            return Alert(
                level='P0',
                type='mempool_front_run',
                evidence={
                    'large_tx': large_tx,
                    'front_run_txs': suspicious,
                    'pattern': 'mempool_monitoring'
                }
            )
```

### 4.2 检测模式 B: 交易序列分析

**原理**: 识别 `小额 → 大额 → 反向` 的操纵序列。

**检测逻辑**:
```python
class SequenceAnalyzer:
    def __init__(self, window_seconds=300):  # 5分钟窗口
        self.window = timedelta(seconds=window_seconds)
        self.wallet_history = defaultdict(deque)

    async def process(self, event: TradeEvent):
        # 记录钱包交易历史
        history = self.wallet_history[event.taker]
        history.append(event)

        # 清理过期数据
        while history and event.timestamp - history[0].timestamp > self.window:
            history.popleft()

        # 检测抢跑序列
        if len(history) >= 3:
            pattern = self.detect_pattern(history)
            if pattern:
                return self.generate_alert(pattern, event)

    def detect_pattern(self, history):
        # 模式1: 小买 → 大买 → 小卖
        if (history[0].side == 'buy' and history[0].size_usd < 1000 and
            history[1].side == 'buy' and history[1].size_usd > 10000 and
            history[2].side == 'sell' and history[2].size_usd < 2000):
            return {
                'type': 'buy_front_run',
                'entry': history[0],
                'target': history[1],
                'exit': history[2],
                'profit': history[2].size_usd - history[0].size_usd
            }
        # 模式2: 小卖 → 大卖 → 小买
        # ... 类似逻辑
```

### 4.3 检测模式 C: 关联账户分析

**原理**: 使用图论检测协同操作的多个钱包。

**检测逻辑**:
```python
import networkx as nx

class SybilDetector:
    def __init__(self):
        self.graph = nx.Graph()
        self.window_minutes = 60

    async def process(self, event: TradeEvent):
        # 添加节点和边
        self.graph.add_node(event.taker, last_seen=event.timestamp)
        self.graph.add_node(event.maker, last_seen=event.timestamp)
        self.graph.add_edge(
            event.taker,
            event.maker,
            market=event.market_id,
            time=event.timestamp
        )

        # 定期检测紧密子图
        if len(self.graph.edges()) % 100 == 0:
            await self.detect_clusters()

    async def detect_clusters(self):
        # 使用社区检测算法
        communities = nx.community_louvain_communities(self.graph)

        for community in communities:
            if len(community) > 5:  # 超过5个钱包的群组
                # 分析交易行为一致性
                if await self.check_coordinated_behavior(community):
                    return Alert(
                        level='P1',
                        type='sybil_coordinated',
                        wallets=list(community)
                    )
```

---

## 5. LLM 增强分析

### 5.1 LLM Prompt 设计

**基础 Prompt 模板**:
```python
FRONT_RUN_ANALYSIS_PROMPT = """
你是一个区块链交易分析专家，专门检测预测市场中的抢跑交易行为。

## 交易序列数据
{transaction_data}

## 市场背景
- 市场: {market_title}
- 当前价格: {current_price}
- 市场事件: {market_event}

## 分析任务
请分析以上交易序列，判断是否构成抢跑交易行为。

请按以下格式输出：

**判断结果**: [是抢跑/正常交易/存疑]
**风险等级**: [P0紧急/P1高风险/P2中风险/P3观察]
**置信度**: [0-1之间的数值]
**原因分析**: [详细解释判断依据，包括:]
- 交易时机分析
- 资金流向分析
- 价格影响分析
**建议行动**: [具体建议]

注意：请基于事实进行分析，不要过度解读。套利交易和抢跑交易的界限需要仔细区分。
"""
```

### 5.2 LLM 调用流程

```python
import openai

async def analyze_with_llm(alert: Alert) -> dict:
    # 构建上下文
    transaction_data = format_transactions(alert.evidence)
    market_context = await get_market_context(alert.market_id)

    # 调用 LLM
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "你是区块链交易安全分析专家。"},
            {"role": "user", "content": FRONT_RUN_ANALYSIS_PROMPT.format(
                transaction_data=transaction_data,
                market_title=market_context['title'],
                current_price=market_context['price'],
                market_event=market_context['event']
            )}
        ],
        temperature=0.1,  # 低温度保证稳定性
        max_tokens=800
    )

    # 解析 LLM 输出
    return parse_llm_response(response.choices[0].message.content)

def parse_llm_response(content: str) -> dict:
    # 使用正则或结构化解析提取字段
    result = {
        'is_front_running': extract_field(content, '判断结果'),
        'risk_level': extract_field(content, '风险等级'),
        'confidence': extract_field(content, '置信度'),
        'reasoning': extract_field(content, '原因分析'),
        'recommendation': extract_field(content, '建议行动')
    }
    return result
```

### 5.3 LLM 降级策略

```python
async def analyze_with_fallback(alert: Alert) -> dict:
    try:
        # 尝试 LLM 分析，设置3秒超时
        llm_result = await asyncio.wait_for(
            analyze_with_llm(alert),
            timeout=3.0
        )
        return llm_result
    except (asyncio.TimeoutError, openai.error.OpenAIError) as e:
        # 降级到规则引擎
        logger.warning(f"LLM analysis failed: {e}, using rule-based fallback")
        return rule_based_analysis(alert)

def rule_based_analysis(alert: Alert) -> dict:
    # 基于预定义规则的简单分析
    profit_ratio = alert.evidence.get('profit', 0) / alert.evidence['entry'].size_usd
    return {
        'is_front_running': '是抢跑' if profit_ratio > 0.05 else '存疑',
        'risk_level': 'P0' if profit_ratio > 0.1 else 'P1',
        'confidence': min(0.9, profit_ratio * 10),
        'reasoning': f'基于规则分析: 获利比例 {profit_ratio:.2%}',
        'recommendation': '建议人工复核' if profit_ratio < 0.05 else '建议立即冻结'
    }
```

---

## 6. 告警系统

### 6.1 告警分级标准

| 级别 | 名称 | 触发条件 | 通知渠道 | 响应时间 |
|------|------|----------|----------|----------|
| P0 | 紧急 | 高确信度 + 涉案金额>$10,000 | 邮件+Slack+电话 | 立即 |
| P1 | 高风险 | 中高确信度 + 金额>$1,000 | 邮件+Slack+短信 | 15分钟 |
| P2 | 中风险 | 低确信度或小金额 | Slack+仪表板 | 1小时 |
| P3 | 观察 | 值得关注的模式 | 仪表板 | 次日 |

### 6.2 告警数据结构

```json
{
  "alert_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-12-30T10:00:00Z",
  "level": "P0",
  "status": "open" | "investigating" | "resolved" | "false_positive",
  "market_id": "polymarket-market-123",
  "suspected_wallets": ["0x123...", "0x456..."],
  "detection_method": "mempool_front_run" | "sequence_analysis" | "sybil_cluster",
  "ml_confidence": 0.92,
  "llm_analysis": {
    "is_front_running": "是抢跑",
    "risk_level": "P0",
    "reasoning": "钱包0x123在大额交易前2秒买入...",
    "recommendation": "建议立即冻结相关账户"
  },
  "evidence": {
    "transactions": [
      {"tx_hash": "0xabc...", "timestamp": "...", "side": "buy", "size_usd": 500}
    ],
    "timing_pattern": "2秒内完成抢跑序列",
    "profit_estimate": 150.00
  },
  "metadata": {
    "detector_version": "1.0.0",
    "processing_time_ms": 234
  }
}
```

### 6.3 告警渠道实现

```python
class AlertDispatcher:
    def __init__(self):
        self.channels = {
            'email': EmailChannel(),
            'slack': SlackChannel(),
            'websocket': WebSocketChannel()
        }

    async def dispatch(self, alert: Alert):
        # 根据级别选择渠道
        channels = self.get_channels_for_level(alert.level)
        tasks = [channel.send(alert) for channel in channels]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_channels_for_level(self, level: str):
        if level == 'P0':
            return ['email', 'slack', 'websocket']
        elif level == 'P1':
            return ['email', 'slack', 'websocket']
        elif level == 'P2':
            return ['slack', 'websocket']
        else:
            return ['websocket']
```

---

## 7. 数据存储设计

### 7.1 数据库 Schema

```sql
-- 交易表 (使用 TimescaleDB 扩展)
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    market_id VARCHAR(100) NOT NULL,
    maker VARCHAR(42) NOT NULL,
    taker VARCHAR(42) NOT NULL,
    side VARCHAR(4) NOT NULL,
    price NUMERIC(18, 8),
    size_usd NUMERIC(18, 2),
    gas_price BIGINT,
    source VARCHAR(20)
);

-- 创建时序数据 hypertable
SELECT create_hypertable('transactions', 'timestamp');

-- 告警表
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    level VARCHAR(2) NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    market_id VARCHAR(100),
    detection_method VARCHAR(50),
    ml_confidence NUMERIC(3, 2),
    llm_analysis JSONB,
    evidence JSONB,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

-- 钱包信誉表
CREATE TABLE wallet_reputation (
    address VARCHAR(42) PRIMARY KEY,
    reputation_score NUMERIC(3, 2) DEFAULT 1.0,
    total_alerts INTEGER DEFAULT 0,
    confirmed_violations INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_transactions_market_time ON transactions(market_id, timestamp DESC);
CREATE INDEX idx_transactions_wallet ON transactions(taker, timestamp DESC);
CREATE INDEX idx_alerts_level_status ON alerts(level, status);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);
```

### 7.2 数据保留策略

```sql
-- 交易数据：保留90天
SELECT add_retention_policy('transactions', INTERVAL '90 days');

-- 告警数据：永久保留（P0/P1），1年（P2/P3）
-- 通过应用层实现逻辑归档
```

---

## 8. 部署架构

### 8.1 Docker Compose 配置

```yaml
version: '3.8'

services:
  # Node.js 数据采集服务
  collector:
    build: ./services/collector
    environment:
      - POLYMARKET_API_KEY=${POLYMARKET_API_KEY}
      - REDIS_URL=redis://redis:6379
      - RPC_NODES=https://polygon-rpc.com,https://eth.llamarpc.com
    deploy:
      replicas: 2
    restart: unless-stopped

  # Python 分析服务
  analyzer:
    build: ./services/analyzer
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://user:pass@postgres:5432/polymarket
      - LLM_API_KEY=${LLM_API_KEY}
    deploy:
      replicas: 2
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # PostgreSQL + TimescaleDB
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      - POSTGRES_DB=polymarket
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # 前端仪表板
  dashboard:
    build: ./frontend
    ports:
      - "3000:3000"
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

### 8.2 Kubernetes 部署（生产环境）

```yaml
# collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: polymarket-collector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      containers:
      - name: collector
        image: your-registry/collector:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: collector-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: polymarket-collector
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 9. 测试策略

### 9.1 单元测试

```python
# tests/test_mempool_detector.py
import pytest
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_mempool_front_run_detection():
    detector = MempoolFrontRunDetector()

    # 模拟交易序列
    events = [
        TradeEvent(tx_hash="0x111", source="mempool", side="buy",
                   size_usd=500, timestamp=datetime.now()),
        TradeEvent(tx_hash="0x222", source="onchain", side="buy",
                   size_usd=15000, timestamp=datetime.now() + timedelta(seconds=1)),
        TradeEvent(tx_hash="0x111", source="onchain", side="sell",
                   size_usd=600, timestamp=datetime.now() + timedelta(seconds=2))
    ]

    for event in events:
        result = await detector.process(event)
        if result:
            assert result.level == 'P0'
            assert result.type == 'mempool_front_run'
            assert 'front_run_txs' in result.evidence
```

### 9.2 回测系统

```python
# backtest.py
async def run_backtest(start_date, end_date):
    # 1. 加载历史数据
    historical_trades = load_historical_data(start_date, end_date)

    # 2. 回放数据
    detected_alerts = []
    for trade in historical_trades:
        alert = await detector.process(trade)
        if alert:
            detected_alerts.append(alert)

    # 3. 与已知案例对比
    known_cases = load_known_manipulation_cases()
    tp, fp, fn = evaluate(detected_alerts, known_cases)

    # 4. 计算指标
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")
```

### 9.3 压力测试

```bash
# 使用 k6 进行压力测试
k6 run --vus 100 --duration 5m stress_test.js
```

---

## 10. 监控与运维

### 10.1 关键指标监控

| 指标 | 类型 | 告警阈值 |
|------|------|----------|
| 采集延迟 | Gauge | >1秒 |
| 分析延迟 | Gauge | >5秒 |
| LLM API 错误率 | Counter | >5% |
| Redis 队列积压 | Gauge | >10000 |
| 检测准确率 | Summary | <80% |

### 10.2 日志规范

```python
import structlog

logger = structlog.get_logger()
logger.info(
    "alert_generated",
    alert_id=alert.id,
    level=alert.level,
    market_id=alert.market_id,
    processing_time_ms=processing_time
)
```

---

## 11. 安全考虑

### 11.1 API 密钥管理

- 使用环境变量或密钥管理服务（如 AWS Secrets Manager）
- 定期轮换 API 密钥
- 最小权限原则

### 11.2 数据隐私

- 钱包地址脱敏存储（可选）
- 符合 GDPR 数据保留要求
- 访问日志审计

---

## 12. 未来扩展

### 12.1 短期优化

- [ ] 增加更多检测模式（如层叠攻击、 Sandwich Attack）
- [ ] 支持多预测市场平台（不仅仅 Polymarket）
- [ ] 机器学习模型训练（使用历史数据）

### 12.2 长期规划

- [ ] 区块链浏览器集成
- [ ] 社区众包验证平台
- [ ] 自动化响应系统（如链上冻结）

---

## 13. 参考资料

[^1]: [CoinDesk: Columbia Study Finds Up to 25% of Polymarket Volume May Be Fake](https://www.coindesk.com/markets/2025/11/07/polymarket-s-trading-volume-may-be-25-fake-columbia-study-finds)

[^2]: [Network-Based Detection of Wash Trading (Columbia Research Paper)](https://papers.ssrn.com/sol3/Delivery.cfm/5714122.pdf?abstractid=5714122&mirid=1)

[^3]: [Polymarket CLOB API Documentation](https://docs.polymarket.com/developers/CLOB/trades/trades-data-api)

[^4]: [Nansen: Blockchain Analysis Tools for Identifying Suspicious Wallets](https://www.nansen.ai/post/blockchain-analysis-tools-identifying-suspicious-wallet-activity)

[^5]: [Chainalysis KYT - Real-time Transaction Monitoring](https://www.chainalysis.com/product/kyt/)

---

**文档版本**: 1.0
**最后更新**: 2025-12-30
