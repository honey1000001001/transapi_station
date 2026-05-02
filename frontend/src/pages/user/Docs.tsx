import React from 'react';
import { Card, Typography, Table, Tag, Divider } from '@arco-design/web-react';
import { MODEL_PRICES } from '../../utils/constants';

const { Title, Paragraph, Text } = Typography;

const Docs: React.FC = () => {
  const modelColumns = [
    { title: '模型 ID', dataIndex: 'id', render: (v: string) => <Text code>{v}</Text> },
    { title: '名称', dataIndex: 'label' },
    { title: '输入价格 (¥/1K token)', dataIndex: 'input', render: (v: number) => v.toFixed(3) },
    { title: '输出价格 (¥/1K token)', dataIndex: 'output', render: (v: number) => v.toFixed(3) },
  ];

  const modelData = Object.entries(MODEL_PRICES).map(([id, info]) => ({
    id, label: info.label, input: info.input, output: info.output,
  }));

  return (
    <div>
      <Title heading={5} style={{ marginBottom: 16 }}>接入文档</Title>

      <Card title="快速开始" style={{ marginBottom: 16 }} bordered={false}>
        <Paragraph>1. 在 "API Key 管理" 页面创建一个新的 API Key</Paragraph>
        <Paragraph>2. 使用以下 Base URL 和您的 API Key 接入：</Paragraph>
        <Paragraph copyable style={{ fontFamily: 'monospace', background: 'var(--color-fill-2)', padding: 12, borderRadius: 4 }}>
          {'Base URL: https://your-domain.com/api/v1\nAPI Key: sk-xxx...xxxx'}
        </Paragraph>
      </Card>

      <Card title="Python SDK 示例" style={{ marginBottom: 16 }} bordered={false}>
        <Paragraph copyable style={{ fontFamily: 'monospace', background: 'var(--color-fill-2)', padding: 12, borderRadius: 4, whiteSpace: 'pre' }}>
{`from openai import OpenAI

client = OpenAI(
    api_key="sk-xxx...xxxx",
    base_url="https://your-domain.com/api/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")`}
        </Paragraph>
      </Card>

      <Card title="curl 示例" style={{ marginBottom: 16 }} bordered={false}>
        <Paragraph copyable style={{ fontFamily: 'monospace', background: 'var(--color-fill-2)', padding: 12, borderRadius: 4, whiteSpace: 'pre' }}>
{`curl https://your-domain.com/api/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx...xxxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}],"stream":true}'`}
        </Paragraph>
      </Card>

      <Card title="模型与价格" style={{ marginBottom: 16 }} bordered={false}>
        <Table columns={modelColumns} data={modelData} rowKey="id" size="small" />
        <Divider />
        <Paragraph type="secondary">计费说明：按实际使用的 Token 数量计费，输入和输出 Token 分开计价。余额不足时请求将被拒绝。</Paragraph>
      </Card>

      <Card title="兼容性" bordered={false}>
        <Paragraph>本服务完全兼容 OpenAI API 格式，支持所有使用 OpenAI SDK 的应用和框架，包括：</Paragraph>
        <Paragraph>
          <Tag color="blue">LangChain</Tag> <Tag color="blue">AutoGen</Tag> <Tag color="blue">Cursor</Tag> <Tag color="blue">Continue</Tag> <Tag color="blue">Open WebUI</Tag>
        </Paragraph>
      </Card>
    </div>
  );
};

export default Docs;
