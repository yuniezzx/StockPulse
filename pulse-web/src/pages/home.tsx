import { Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col gap-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">StockPulse</h1>
        <p className="text-muted-foreground">
          A 股短中线个人选股决策系统，提供选股、持仓追踪、风险提示与策略校验的闭环功能。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Link to="/analysis" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>① 个股分析</CardTitle>
              <CardDescription>输入股票代码查看完整技术分析</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/picks" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>② 选股</CardTitle>
              <CardDescription>每日傍晚跑出的候选股票</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/risk-signals" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>③ 风控信号</CardTitle>
              <CardDescription>次日早晨级风控扫描，触发卖出信号</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/portfolio" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>④ 真实持仓</CardTitle>
              <CardDescription>管理真实持仓，追踪盈亏</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/virtual-portfolio" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>④ 虚拟仓</CardTitle>
              <CardDescription>系统从候选股自动建立的虚拟仓</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/strategies" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>⑤⑥ 策略与权重</CardTitle>
              <CardDescription>查看策略列表与当前权重</CardDescription>
            </CardHeader>
          </Card>
        </Link>
        <Link to="/evaluations" className="block h-full">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle>⑤ 校验报告</CardTitle>
              <CardDescription>策略校验报告：胜率、夏普等</CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
