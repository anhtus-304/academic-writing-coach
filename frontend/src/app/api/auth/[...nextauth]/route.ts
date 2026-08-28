import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

const nextAuth = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
  ],
  pages: {
    signIn: "/auth/signin",
  },
})

export const { GET, POST } = nextAuth.handlers