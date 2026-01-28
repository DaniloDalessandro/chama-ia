import {
  Mail,
  Phone,
  Users,
  AlertCircle,
  Zap,
  Clock,
  MessageSquare,
  Headphones,
  Bell,
  CheckCircle,
  PhoneCall,
  UserCheck,
  MailOpen,
  Timer
} from "lucide-react"

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-background">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-muted/30" />

      {/* Animated blobs */}
      <div className="absolute inset-0">
        <div className="absolute top-0 -left-4 w-96 h-96 bg-primary/10 rounded-full mix-blend-multiply filter blur-3xl animate-blob" />
        <div className="absolute -bottom-8 right-0 w-96 h-96 bg-primary/10 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000" />
      </div>

      {/* Floating icons */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Email */}
        <div className="absolute top-[15%] left-[10%] text-primary animate-icon-float">
          <Mail className="w-24 h-24" />
        </div>
        <div className="absolute top-[60%] right-[8%] text-primary animate-icon-float animation-delay-2000">
          <MailOpen className="w-18 h-18" />
        </div>
        <div className="absolute bottom-[25%] left-[15%] text-primary animate-icon-float animation-delay-3000">
          <Mail className="w-16 h-16" />
        </div>

        {/* Phone */}
        <div className="absolute top-[25%] right-[15%] text-primary animate-icon-float animation-delay-1000">
          <Phone className="w-20 h-20" />
        </div>
        <div className="absolute bottom-[35%] right-[20%] text-primary animate-icon-float animation-delay-4000">
          <PhoneCall className="w-16 h-16" />
        </div>
        <div className="absolute top-[70%] left-[8%] text-primary animate-icon-float animation-delay-2500">
          <Headphones className="w-18 h-18" />
        </div>

        {/* Users */}
        <div className="absolute top-[10%] right-[30%] text-primary animate-icon-float animation-delay-500">
          <Users className="w-18 h-18" />
        </div>
        <div className="absolute bottom-[15%] right-[12%] text-primary animate-icon-float animation-delay-3500">
          <UserCheck className="w-20 h-20" />
        </div>
        <div className="absolute top-[45%] left-[5%] text-primary animate-icon-float animation-delay-1500">
          <Users className="w-16 h-16" />
        </div>

        {/* Urgency */}
        <div className="absolute top-[20%] left-[25%] text-primary animate-icon-float animation-delay-2000">
          <AlertCircle className="w-16 h-16" />
        </div>
        <div className="absolute bottom-[40%] left-[25%] text-primary animate-icon-float animation-delay-4500">
          <Bell className="w-18 h-18" />
        </div>
        <div className="absolute top-[75%] right-[25%] text-primary animate-icon-float animation-delay-1000">
          <AlertCircle className="w-14 h-14" />
        </div>

        {/* Speed/Time */}
        <div className="absolute top-[35%] right-[5%] text-primary animate-icon-float animation-delay-3000">
          <Zap className="w-18 h-18" />
        </div>
        <div className="absolute bottom-[20%] left-[30%] text-primary animate-icon-float animation-delay-500">
          <Clock className="w-16 h-16" />
        </div>
        <div className="absolute top-[55%] right-[30%] text-primary animate-icon-float animation-delay-2500">
          <Timer className="w-16 h-16" />
        </div>

        {/* Messages */}
        <div className="absolute top-[40%] left-[18%] text-primary animate-icon-float animation-delay-1500">
          <MessageSquare className="w-16 h-16" />
        </div>
        <div className="absolute bottom-[30%] right-[35%] text-primary animate-icon-float animation-delay-3500">
          <MessageSquare className="w-14 h-14" />
        </div>

        {/* Success */}
        <div className="absolute top-[85%] left-[20%] text-primary animate-icon-float animation-delay-4000">
          <CheckCircle className="w-16 h-16" />
        </div>
        <div className="absolute top-[8%] left-[40%] text-primary animate-icon-float animation-delay-2000">
          <CheckCircle className="w-14 h-14" />
        </div>
      </div>

      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }}
      />

      {/* Content */}
      <div className="w-full max-w-md p-6 relative z-10">
        {children}
      </div>
    </div>
  )
}
