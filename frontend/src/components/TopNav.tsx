import { NavLink } from "@/components/NavLink";
import { LayoutDashboard, Radio, Inbox, Activity, LogOut, User } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { getAuthSession, logout } from "@/api/login.ts";

const navItems = [
  { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
  { title: "Live Flows", url: "/live-flows", icon: Radio },
  { title: "Routed Queue", url: "/routed-queue", icon: Inbox },
  { title: "System Health", url: "/system-health", icon: Activity },
];

export function TopNav() {
  const navigate = useNavigate();
  const session = getAuthSession();

  const displayName =
      session?.user.email || session?.user.username || "User";

  const handleSignOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
      <header className="h-12 flex items-center justify-between border-b border-border px-6 bg-card shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 mr-4">
            <img
                src="/logo.png"
                alt="DeepEncryptNet logo"
                className="h-7 w-7 rounded-md object-contain shrink-0"
            />
            <span className="text-sm font-semibold text-foreground hidden sm:inline">
              DeepEncryptNet
            </span>
          </div>

          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
                <NavLink
                    key={item.title}
                    to={item.url}
                    end={item.url === "/"}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                    activeClassName="bg-accent text-foreground font-medium"
                >
                  <item.icon className="h-3.5 w-3.5" />
                  <span className="hidden md:inline">{item.title}</span>
                </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-secondary flex items-center justify-center">
              <User className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <span className="text-xs text-muted-foreground hidden sm:inline">
            {displayName}
          </span>
          </div>

          <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              title="Sign out"
              onClick={handleSignOut}
          >
            <LogOut className="h-3.5 w-3.5" />
          </Button>
        </div>
      </header>
  );
}