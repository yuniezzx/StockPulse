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

export default function StrategiesPage() {
  return (
    <FeaturePlaceholder
      title="策略与权重"
      subtitle="⑤⑥ Strategies · /strategies"
      description="查看策略列表、当前权重，审核系统建议的权重调整。"
    />
  );
}
