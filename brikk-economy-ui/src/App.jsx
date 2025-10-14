import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { 
  CreditCard, 
  DollarSign, 
  TrendingUp, 
  Star, 
  Award, 
  Users, 
  Activity,
  Plus,
  Minus,
  ArrowUpRight,
  ArrowDownRight,
  Shield,
  Zap
} from 'lucide-react'
import './App.css'

function App() {
  const [credits, setCredits] = useState(1250)
  const [reputation, setReputation] = useState(4.7)
  const [totalEarned, setTotalEarned] = useState(5420)
  const [totalSpent, setTotalSpent] = useState(4170)
  const [topUpAmount, setTopUpAmount] = useState('')

  // Simulated real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate small fluctuations in reputation
      setReputation(prev => Math.max(0, Math.min(5, prev + (Math.random() - 0.5) * 0.01)))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const recentTransactions = [
    { id: 1, type: 'earned', amount: 50, description: 'Workflow completion bonus', timestamp: '2 hours ago', agent: 'DataProcessor Alpha' },
    { id: 2, type: 'spent', amount: 25, description: 'API coordination request', timestamp: '4 hours ago', agent: 'ML Coordinator Beta' },
    { id: 3, type: 'earned', amount: 75, description: 'High-quality task execution', timestamp: '6 hours ago', agent: 'Security Monitor Delta' },
    { id: 4, type: 'spent', amount: 15, description: 'Resource allocation', timestamp: '8 hours ago', agent: 'Cache Manager Epsilon' },
    { id: 5, type: 'earned', amount: 100, description: 'Performance milestone', timestamp: '1 day ago', agent: 'API Gateway Gamma' }
  ]

  const reputationMetrics = [
    { label: 'Task Success Rate', value: 94.2, max: 100, color: 'bg-green-500' },
    { label: 'Response Time', value: 87.5, max: 100, color: 'bg-blue-500' },
    { label: 'Reliability Score', value: 96.8, max: 100, color: 'bg-purple-500' },
    { label: 'Collaboration Rating', value: 91.3, max: 100, color: 'bg-orange-500' }
  ]

  const handleTopUp = () => {
    if (topUpAmount && !isNaN(topUpAmount) && parseFloat(topUpAmount) > 0) {
      const amount = parseFloat(topUpAmount)
      setCredits(prev => prev + amount)
      setTotalEarned(prev => prev + amount)
      setTopUpAmount('')
      // In a real app, this would integrate with Stripe
      alert(`Successfully added ${amount} credits to your account!`)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  Brikk Economy
                </h1>
                <p className="text-sm text-slate-400">Agent Coordination Platform</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="border-green-500 text-green-400">
                <Shield className="w-3 h-3 mr-1" />
                System Healthy
              </Badge>
              <div className="text-right">
                <p className="text-sm text-slate-400">Organization</p>
                <p className="font-medium">Acme Corp</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Available Credits</CardTitle>
              <DollarSign className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{credits.toLocaleString()}</div>
              <p className="text-xs text-slate-400 mt-1">
                +12% from last month
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Reputation Score</CardTitle>
              <Star className="h-4 w-4 text-yellow-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{reputation.toFixed(1)}/5.0</div>
              <div className="flex items-center mt-1">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`h-3 w-3 ${
                      i < Math.floor(reputation) ? 'text-yellow-400 fill-current' : 'text-slate-600'
                    }`}
                  />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Total Earned</CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{totalEarned.toLocaleString()}</div>
              <p className="text-xs text-slate-400 mt-1">
                Lifetime earnings
              </p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Total Spent</CardTitle>
              <Activity className="h-4 w-4 text-red-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{totalSpent.toLocaleString()}</div>
              <p className="text-xs text-slate-400 mt-1">
                Platform usage costs
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-slate-800/50 border-slate-700">
            <TabsTrigger value="dashboard" className="data-[state=active]:bg-slate-700">Dashboard</TabsTrigger>
            <TabsTrigger value="credits" className="data-[state=active]:bg-slate-700">Credits</TabsTrigger>
            <TabsTrigger value="reputation" className="data-[state=active]:bg-slate-700">Reputation</TabsTrigger>
            <TabsTrigger value="transactions" className="data-[state=active]:bg-slate-700">Transactions</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Credit Balance Chart */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white">Credit Balance Trend</CardTitle>
                  <CardDescription className="text-slate-400">
                    Your credit balance over the last 30 days
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64 flex items-center justify-center text-slate-400">
                    <div className="text-center">
                      <TrendingUp className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                      <p>Credit trend visualization</p>
                      <p className="text-sm">Chart component would be rendered here</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Reputation Breakdown */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white">Reputation Breakdown</CardTitle>
                  <CardDescription className="text-slate-400">
                    Performance metrics contributing to your reputation
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {reputationMetrics.map((metric, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-300">{metric.label}</span>
                        <span className="text-white font-medium">{metric.value}%</span>
                      </div>
                      <Progress value={metric.value} className="h-2" />
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="credits" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Up Credits */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white flex items-center">
                    <CreditCard className="w-5 h-5 mr-2" />
                    Top Up Credits
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Add credits to your account via Stripe integration
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="amount" className="text-slate-300">Amount (Credits)</Label>
                    <Input
                      id="amount"
                      type="number"
                      placeholder="Enter amount"
                      value={topUpAmount}
                      onChange={(e) => setTopUpAmount(e.target.value)}
                      className="bg-slate-700 border-slate-600 text-white"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTopUpAmount('100')}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      +100
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTopUpAmount('500')}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      +500
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTopUpAmount('1000')}
                      className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      +1000
                    </Button>
                  </div>
                  <Button onClick={handleTopUp} className="w-full bg-blue-600 hover:bg-blue-700">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Credits
                  </Button>
                </CardContent>
              </Card>

              {/* Credit Usage Stats */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white">Usage Statistics</CardTitle>
                  <CardDescription className="text-slate-400">
                    How you've been using your credits
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                      <div className="flex items-center">
                        <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
                        <span className="text-slate-300">API Calls</span>
                      </div>
                      <span className="text-white font-medium">2,847 credits</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                      <div className="flex items-center">
                        <div className="w-3 h-3 bg-blue-500 rounded-full mr-3"></div>
                        <span className="text-slate-300">Workflow Execution</span>
                      </div>
                      <span className="text-white font-medium">1,123 credits</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                      <div className="flex items-center">
                        <div className="w-3 h-3 bg-purple-500 rounded-full mr-3"></div>
                        <span className="text-slate-300">Data Processing</span>
                      </div>
                      <span className="text-white font-medium">200 credits</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="reputation" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Reputation Score */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white flex items-center">
                    <Award className="w-5 h-5 mr-2" />
                    Reputation Score
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Your overall performance rating in the network
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-center space-y-4">
                  <div className="text-6xl font-bold text-white">{reputation.toFixed(1)}</div>
                  <div className="flex justify-center space-x-1">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`h-6 w-6 ${
                          i < Math.floor(reputation) ? 'text-yellow-400 fill-current' : 'text-slate-600'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-slate-400">Based on 1,247 interactions</p>
                  <Badge className="bg-green-600 text-white">
                    Excellent Performance
                  </Badge>
                </CardContent>
              </Card>

              {/* Reputation History */}
              <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-white">Recent Feedback</CardTitle>
                  <CardDescription className="text-slate-400">
                    Latest reputation updates from agent interactions
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                      <span className="text-slate-300">Task completed successfully</span>
                    </div>
                    <span className="text-green-400 text-sm">+0.1</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
                      <span className="text-slate-300">Fast response time</span>
                    </div>
                    <span className="text-blue-400 text-sm">+0.05</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
                      <span className="text-slate-300">High-quality output</span>
                    </div>
                    <span className="text-purple-400 text-sm">+0.15</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="transactions" className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Recent Transactions</CardTitle>
                <CardDescription className="text-slate-400">
                  Your latest credit earnings and expenditures
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentTransactions.map((transaction) => (
                    <div key={transaction.id} className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-full ${
                          transaction.type === 'earned' ? 'bg-green-600/20' : 'bg-red-600/20'
                        }`}>
                          {transaction.type === 'earned' ? (
                            <ArrowUpRight className="w-4 h-4 text-green-400" />
                          ) : (
                            <ArrowDownRight className="w-4 h-4 text-red-400" />
                          )}
                        </div>
                        <div>
                          <p className="text-white font-medium">{transaction.description}</p>
                          <p className="text-sm text-slate-400">{transaction.agent} • {transaction.timestamp}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`font-bold ${
                          transaction.type === 'earned' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {transaction.type === 'earned' ? '+' : '-'}{transaction.amount} credits
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default App
