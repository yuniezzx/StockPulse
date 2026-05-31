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

export default function VirtualPortfolioPage() {
  return (
    <FeaturePlaceholder
      title="虚拟仓"
      subtitle="④ Virtual Portfolio · /virtual-portfolio"
      description="系统从候选股自动建立的虚拟仓，验证策略实战表现。"
    />
  );
}
