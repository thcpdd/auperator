import { redirect } from "next/navigation";

export default function Home() {
  // Redirect to chat page by default
  redirect("/chat");
}
