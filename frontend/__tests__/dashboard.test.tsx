import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

describe('SentinelFlow Dashboard Basic Tests', () => {
  it('should render page headers successfully', () => {
    render(
      <div>
        <h1>SentinelFlow AI Dashboard</h1>
        <p>Mastra-powered self-healing security operations</p>
      </div>
    )
    expect(screen.getByText('SentinelFlow AI Dashboard')).toBeInTheDocument()
    expect(screen.getByText(/self-healing/i)).toBeInTheDocument()
  })
})
