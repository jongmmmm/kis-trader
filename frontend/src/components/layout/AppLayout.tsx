import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import AuctionOverlay from '../auction/AuctionOverlay'

export default function AppLayout() {
  return (
    <>
      <Navbar />
      <div className="d-flex app-body">
        <Sidebar />
        <main className="flex-grow-1 p-4" style={{ minWidth: 0 }}>
          <Outlet />
        </main>
      </div>
      <AuctionOverlay />
    </>
  )
}
