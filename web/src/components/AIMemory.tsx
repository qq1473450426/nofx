import useSWR from 'swr';
import type { Language } from '../i18n/translations';

interface TradeEntry {
  trade_id: number;
  cycle: number;
  timestamp: string;
  market_regime: string;
  regime_stage: string;
  action: string;
  symbol: string;
  side: string;
  signals: string[];
  reasoning: string;
  predicted_direction?: string;
  predicted_prob?: number;
  predicted_move?: number;
  entry_price?: number;
  exit_price?: number;
  position_pct: number;
  leverage?: number;
  hold_minutes?: number;
  return_pct: number;
  result: string;
}

interface MemoryData {
  version: string;
  trader_id: string;
  created_at: string;
  updated_at: string;
  total_trades: number;
  status: string;
  recent_trades: TradeEntry[];
  hard_constraints: string[];
}

export function AIMemory({ traderId, language }: { traderId: string; language: Language }) {
  console.log('🧠 AIMemory component rendered, traderId:', traderId);

  const { data: memory, error, isLoading } = useSWR<MemoryData>(
    traderId ? `memory-${traderId}` : null,
    async () => {
      console.log('📡 Fetching memory data for:', traderId);
      // 动态检测环境：本地开发用 localhost，生产环境用当前域名
      const baseUrl = window.location.hostname === 'localhost'
        ? 'http://localhost:8080'
        : `http://${window.location.hostname}:8080`;
      const response = await fetch(`${baseUrl}/api/memory?trader_id=${traderId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('✅ Memory data received:', data);
      return data;
    },
    {
      refreshInterval: 10000, // 10秒刷新
      revalidateOnFocus: false,
    }
  );

  console.log('🔍 AIMemory state:', { hasData: !!memory, hasError: !!error, isLoading });

  if (error) {
    console.error('❌ Memory loading error:', error);
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-3">⚠️</div>
        <div className="text-sm" style={{ color: '#F6465D' }}>
          {language === 'zh' ? '记忆加载失败' : 'Failed to load memory'}
        </div>
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-3">🧠</div>
        <div className="text-sm" style={{ color: '#848E9C' }}>
          {language === 'zh' ? '加载中...' : 'Loading...'}
        </div>
      </div>
    );
  }

  // 计算统计数据
  const completedTrades = memory.recent_trades.filter(t => t.result).length;
  const winCount = memory.recent_trades.filter(t => t.result === 'win').length;
  const lossCount = memory.recent_trades.filter(t => t.result === 'loss').length;
  const winRate = completedTrades > 0 ? (winCount / completedTrades) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* 记忆状态概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="p-3 rounded" style={{ background: '#1E2329', border: '1px solid #2B3139' }}>
          <div className="text-xs mb-1" style={{ color: '#848E9C' }}>
            {language === 'zh' ? '总交易数' : 'Total Trades'}
          </div>
          <div className="text-xl font-bold" style={{ color: '#EAECEF' }}>
            {memory.total_trades}
          </div>
          <div className="text-xs mt-1" style={{ color: '#848E9C' }}>
            {memory.status === 'learning'
              ? (language === 'zh' ? '学习中' : 'Learning')
              : (language === 'zh' ? '成熟期' : 'Mature')}
          </div>
        </div>

        <div className="p-3 rounded" style={{ background: '#1E2329', border: '1px solid #2B3139' }}>
          <div className="text-xs mb-1" style={{ color: '#848E9C' }}>
            {language === 'zh' ? '近期胜率' : 'Recent Win Rate'}
          </div>
          <div className="text-xl font-bold" style={{ color: winRate >= 50 ? '#0ECB81' : '#F6465D' }}>
            {winRate.toFixed(1)}%
          </div>
          <div className="text-xs mt-1" style={{ color: '#848E9C' }}>
            {winCount}W / {lossCount}L
          </div>
        </div>

        <div className="p-3 rounded" style={{ background: '#1E2329', border: '1px solid #2B3139' }}>
          <div className="text-xs mb-1" style={{ color: '#848E9C' }}>
            {language === 'zh' ? '记忆深度' : 'Memory Depth'}
          </div>
          <div className="text-xl font-bold" style={{ color: '#EAECEF' }}>
            {memory.recent_trades.length}
          </div>
          <div className="text-xs mt-1" style={{ color: '#848E9C' }}>
            {language === 'zh' ? '最近20笔' : 'Last 20'}
          </div>
        </div>

        <div className="p-3 rounded" style={{ background: '#1E2329', border: '1px solid #2B3139' }}>
          <div className="text-xs mb-1" style={{ color: '#848E9C' }}>
            {language === 'zh' ? '活跃度' : 'Activity'}
          </div>
          <div className="text-xl font-bold" style={{ color: '#F0B90B' }}>
            {memory.total_trades >= 100 ? '🔥' : '🌱'}
          </div>
          <div className="text-xs mt-1" style={{ color: '#848E9C' }}>
            {memory.total_trades >= 100
              ? (language === 'zh' ? '活跃' : 'Active')
              : `${100 - memory.total_trades} to 100`}
          </div>
        </div>
      </div>

      {/* 最近交易记录 */}
      <div className="space-y-3">
        {memory.recent_trades.slice().reverse().slice(0, 10).map((trade) => (
          <TradeMemoryCard key={trade.trade_id} trade={trade} language={language} />
        ))}

        {memory.recent_trades.length === 0 && (
          <div className="text-center py-12">
            <div className="text-5xl mb-3">📝</div>
            <div className="text-base font-semibold mb-2" style={{ color: '#EAECEF' }}>
              {language === 'zh' ? '暂无交易记忆' : 'No Trade Memory Yet'}
            </div>
            <div className="text-sm" style={{ color: '#848E9C' }}>
              {language === 'zh'
                ? 'AI首次交易后将开始记录学习'
                : 'Memory will start recording after first trade'}
            </div>
          </div>
        )}
      </div>

      {/* 硬约束提示 */}
      <div className="mt-6 p-4 rounded" style={{ background: 'rgba(240, 185, 11, 0.05)', border: '1px solid rgba(240, 185, 11, 0.2)' }}>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">🛡️</span>
          <div className="text-sm font-semibold" style={{ color: '#F0B90B' }}>
            {language === 'zh' ? '基础风控约束' : 'Hard Constraints'}
          </div>
        </div>
        <div className="space-y-1.5 text-xs" style={{ color: '#848E9C' }}>
          {memory.hard_constraints.map((constraint, i) => (
            <div key={i} className="flex items-start gap-2">
              <span style={{ color: '#F0B90B' }}>•</span>
              <span>{constraint}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TradeMemoryCard({ trade, language }: { trade: TradeEntry; language: Language }) {
  const timeSince = (timestamp: string) => {
    const now = new Date().getTime();
    const then = new Date(timestamp).getTime();
    const diff = Math.floor((now - then) / 1000);

    if (diff < 60) return language === 'zh' ? '刚才' : 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}${language === 'zh' ? '分钟前' : 'm ago'}`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}${language === 'zh' ? '小时前' : 'h ago'}`;
    return `${Math.floor(diff / 86400)}${language === 'zh' ? '天前' : 'd ago'}`;
  };

  const getRegimeEmoji = (regime: string) => {
    switch (regime) {
      case 'markup': return '📈';
      case 'accumulation': return '🔄';
      case 'distribution': return '📊';
      case 'markdown': return '📉';
      default: return '❓';
    }
  };

  const getResultColor = (result: string) => {
    if (result === 'win') return '#0ECB81';
    if (result === 'loss') return '#F6465D';
    return '#848E9C';
  };

  return (
    <div
      className="p-4 rounded-lg hover:scale-[1.01] transition-transform"
      style={{
        background: '#1E2329',
        border: '1px solid #2B3139',
        boxShadow: trade.result ? `0 0 0 1px ${getResultColor(trade.result)}33` : 'none'
      }}
    >
      {/* 头部：周期 + 时间 + 市场体制 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: '#2B3139', color: '#848E9C' }}>
            #{trade.cycle}
          </span>
          <span className="text-xs" style={{ color: '#848E9C' }}>
            {timeSince(trade.timestamp)}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>{getRegimeEmoji(trade.market_regime)}</span>
          <span className="text-xs" style={{ color: '#848E9C' }}>
            {trade.market_regime}
          </span>
        </div>
      </div>

      {/* 主要信息：Action + Symbol */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-sm font-bold`}
            style={trade.action === 'open'
              ? { background: trade.side === 'long' ? 'rgba(14, 203, 129, 0.15)' : 'rgba(246, 70, 93, 0.15)',
                  color: trade.side === 'long' ? '#0ECB81' : '#F6465D' }
              : { background: '#2B3139', color: '#848E9C' }
            }>
            {trade.action.toUpperCase()} {trade.side ? trade.side.toUpperCase() : ''}
          </span>
          <span className="font-mono font-bold" style={{ color: '#EAECEF' }}>
            {trade.symbol}
          </span>
        </div>

        {trade.result && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs" style={{ color: getResultColor(trade.result) }}>
              {trade.result === 'win' ? '✅' : trade.result === 'loss' ? '❌' : '➖'}
            </span>
            <span className="font-mono font-bold" style={{ color: getResultColor(trade.result) }}>
              {trade.return_pct >= 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* 预测信息 */}
      {trade.predicted_direction && (
        <div className="mb-2 p-2 rounded text-xs" style={{ background: '#0B0E11' }}>
          <span style={{ color: '#848E9C' }}>{language === 'zh' ? '预测' : 'Prediction'}:</span>{' '}
          <span style={{ color: trade.predicted_direction === 'up' ? '#0ECB81' : '#F6465D' }}>
            {trade.predicted_direction === 'up' ? '↑' : '↓'}
          </span>{' '}
          {trade.predicted_prob && (
            <span style={{ color: '#EAECEF' }}>
              {(trade.predicted_prob * 100).toFixed(0)}%
            </span>
          )}
        </div>
      )}

      {/* 推理 */}
      <div className="text-xs leading-relaxed" style={{ color: '#848E9C' }}>
        {trade.reasoning.length > 150
          ? `${trade.reasoning.slice(0, 150)}...`
          : trade.reasoning}
      </div>

      {/* 底部：信号 + 详情 */}
      {trade.signals && trade.signals.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {trade.signals.slice(0, 3).map((signal, i) => (
            <span key={i} className="text-xs px-2 py-0.5 rounded"
              style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#6366F1' }}>
              {signal}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
