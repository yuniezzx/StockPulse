import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">仪表盘（建设中）</h1>
        <p className="text-muted-foreground">全局核心信息概览</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="min-h-[200px]">
          <CardHeader>
            <CardTitle>今日候选</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center text-muted-foreground h-full pb-6">
            预留区位
          </CardContent>
        </Card>
        
        <Card className="min-h-[200px]">
          <CardHeader>
            <CardTitle>当前持仓</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center text-muted-foreground h-full pb-6">
            预留区位
          </CardContent>
        </Card>
        
        <Card className="min-h-[200px]">
          <CardHeader>
            <CardTitle>风险提示</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center text-muted-foreground h-full pb-6">
            预留区位
          </CardContent>
        </Card>
        
        <Card className="min-h-[200px]">
          <CardHeader>
            <CardTitle>策略概览</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center text-muted-foreground h-full pb-6">
            预留区位
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
