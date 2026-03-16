import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MangaDich — Dịch Manga AI",
  description: "Dịch truyện tranh sang tiếng Việt với AI — OCR, xóa text, dịch thuật thông minh theo thể loại",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>
        {children}
      </body>
    </html>
  );
}
