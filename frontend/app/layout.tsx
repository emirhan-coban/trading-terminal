import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'Nexus Bot',description:'Sade OKX paper trading botu'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="tr"><body>{children}</body></html>}
