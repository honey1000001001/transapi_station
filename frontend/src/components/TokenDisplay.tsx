import React from 'react';
import { Typography } from '@arco-design/web-react';
import { formatNumber } from '../utils/format';

interface TokenDisplayProps {
  prompt: number | undefined | null;
  completion: number | undefined | null;
  showBreakdown?: boolean;
}

const TokenDisplay: React.FC<TokenDisplayProps> = ({ prompt, completion, showBreakdown = true }) => {
  const p = prompt ?? 0;
  const c = completion ?? 0;
  const total = p + c;

  if (!showBreakdown) {
    return <Typography.Text>{formatNumber(total)}</Typography.Text>;
  }

  return (
    <Typography.Text style={{ fontSize: 13 }}>
      <span title={`输入: ${formatNumber(p)} / 输出: ${formatNumber(c)} / 总计: ${formatNumber(total)}`}>
        {formatNumber(p)} / {formatNumber(c)} / {formatNumber(total)}
      </span>
    </Typography.Text>
  );
};

export default TokenDisplay;
