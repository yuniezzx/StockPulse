function FeaturePlaceholder({ title, subtitle, description }: { title: string; subtitle: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 p-6">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        {description}
      </p>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <FeaturePlaceholder
      title="个股分析"
      subtitle="① Analysis · /analysis"
      description="输入股票代码查看完整技术分析：指标、形态、结论。"
    />
  );
}
