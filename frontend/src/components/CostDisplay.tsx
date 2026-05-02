import React from 'react';
import { Typography } from '@arco-design/web-react';
import { formatCostShort } from '../utils/format';

interface CostDisplayProps {
  cost: number | undefined | null;
}

const CostDisplay: React.FC<CostDisplayProps> = ({ cost }) => {
  return (
    <Typography.Text style={{ fontFamily: 'monospace' }}>
      {formatCostShort(cost)}
    </Typography.Text>
  );
};

export default CostDisplay;
