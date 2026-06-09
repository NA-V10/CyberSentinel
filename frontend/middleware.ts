import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/incidents(.*)",
  "/graph(.*)",
  "/reports(.*)",
  "/feedback(.*)",
  "/admin(.*)",
  "/war-room(.*)",
  "/simulation(.*)",
  "/mcp-tools(.*)",
  "/memory(.*)",
  "/audit-logs(.*)",
]);

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

// When Clerk keys are not yet configured, skip auth so the app is usable
// during local dev without a Clerk account.
export default clerkMiddleware((auth, req) => {
  if (!isClerkConfigured) {
    return NextResponse.next();
  }
  if (isProtectedRoute(req)) {
    auth().protect();
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
