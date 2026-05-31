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

export default function SettingsPage() {
  return (
    <FeaturePlaceholder
      title="设置"
      subtitle="Settings · /settings"
      description="用户偏好配置：通知通道、订阅赛道、推送时间。"
    />
  );
}
