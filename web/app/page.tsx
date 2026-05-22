"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import useEmblaCarousel from 'embla-carousel-react'
import { useCallback } from 'react'

export default function Page() {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, align: 'start' })

  const scrollPrev = useCallback(() => {
    if (emblaApi) emblaApi.scrollPrev()
  }, [emblaApi])

  const scrollNext = useCallback(() => {
    if (emblaApi) emblaApi.scrollNext()
  }, [emblaApi])

  return (
    <div className="min-h-screen bg-[#f8f8f8]">
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between p-6 bg-[#f8f8f8]/80 backdrop-blur-sm border-b border-gray-100">
        <div className="flex space-x-2">
          <div className="h-2 w-2 rounded-full bg-blue-600 animate-pulse"></div>
          <div className="h-2 w-2 rounded-full bg-green-600 animate-pulse" style={{ animationDelay: '0.5s' }}></div>
        </div>
        <div className="flex items-center space-x-8">
          <Link href="#how-it-works" className="text-sm tracking-wide hover:text-blue-600 transition-colors font-medium">
            HOW IT WORKS
          </Link>
          <Link href="#features" className="text-sm tracking-wide hover:text-blue-600 transition-colors font-medium">
            FEATURES
          </Link>
          <Link href="#faq" className="text-sm tracking-wide hover:text-blue-600 transition-colors font-medium">
            FAQ
          </Link>
        </div>
      </header>

      <main className="relative px-6 md:px-12 lg:px-24 pt-32">
        {/* Continuous gradient blob in top right corner */}
        <div
          className="fixed right-0 top-0 h-[600px] w-[600px] rounded-full bg-gradient-to-br from-blue-400 via-cyan-300 to-green-300 opacity-40 blur-3xl pointer-events-none"
          style={{
            animation: 'blobFloat 20s ease-in-out infinite'
          }}
        />

        {/* Hero Section */}
        <section className="relative pb-32 min-h-[90vh] flex flex-col justify-center max-w-7xl mx-auto">
          <div className="mb-8 animate-fade-in">
            <span className="text-8xl md:text-9xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
              Sieve
            </span>
          </div>
          
          <h1 className="max-w-4xl text-5xl md:text-6xl font-light leading-[1.2] tracking-tight animate-fade-in-delay">
            Never Miss a Deadline from Your Group Chats Again
          </h1>

          <p className="mt-8 max-w-2xl text-lg leading-relaxed text-gray-700 animate-fade-in-delay-2">
            Automatically extracts tasks and deadlines from your Telegram group messages
            and sends you personal reminders—so you can focus on what matters.
          </p>

          <div className="mt-12 flex gap-4 animate-fade-in-delay-3">
            <a href="https://t.me/sieve7_bot" target="_blank" rel="noopener noreferrer">
              <Button className="rounded-full border-2 bg-blue-600 border-blue-600 px-10 py-6 text-base text-white hover:bg-blue-700 hover:border-blue-700 hover:scale-105 transition-all duration-300 font-medium">
                Try Sieve Bot
              </Button>
            </a>
            <a href="#how-it-works">
              <Button variant="outline" className="rounded-full border-2 border-blue-600 text-blue-600 px-10 py-6 text-base hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium">
                See How It Works
              </Button>
            </a>
          </div>

          <div className="mt-12 flex gap-10 text-sm text-gray-600 tracking-wide font-medium">
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-600"></span>
              Free Forever
            </span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-green-600"></span>
              30-Second Setup
            </span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-600"></span>
              Privacy First
            </span>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
        </div>

        {/* Problem Section */}
        <section className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              The Problem
            </h2>
            <p className="text-xl text-gray-500">
              Tired of Missing Important Deadlines Buried in Group Chats?
            </p>
          </div>

          <div className="grid gap-12 md:grid-cols-3">
            <div className="group p-8 border border-gray-200 hover:border-blue-600 hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-12 bg-gradient-to-r from-blue-600 to-cyan-600 mb-6"></div>
              <h3 className="text-xl font-medium mb-4">Information Overload</h3>
              <p className="text-gray-600 leading-relaxed">
                Your study and work groups have hundreds of messages daily. Important deadlines get buried under casual chat.
                You scroll back frantically trying to find when that assignment was due.
              </p>
            </div>

            <div className="group p-8 border border-gray-200 hover:border-green-600 hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-12 bg-gradient-to-r from-green-600 to-cyan-600 mb-6"></div>
              <h3 className="text-xl font-medium mb-4">Manual Tracking is Tedious</h3>
              <p className="text-gray-600 leading-relaxed">
                Copy-pasting tasks to your calendar takes time. You forget to set reminders for every deadline.
                Different groups, different deadlines—hard to keep track.
              </p>
            </div>

            <div className="group p-8 border border-gray-200 hover:border-cyan-600 hover:shadow-lg transition-all duration-300">
              <div className="h-1 w-12 bg-gradient-to-r from-cyan-600 to-blue-600 mb-6"></div>
              <h3 className="text-xl font-medium mb-4">The Consequences</h3>
              <p className="text-gray-600 leading-relaxed">
                Missed submissions and late penalties. Stress from last-minute rushes.
                Letting your team down.
              </p>
            </div>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
        </div>

        {/* Solution Section */}
        <section className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              The Solution
            </h2>
            <p className="text-xl text-gray-700">
              Meet <span className="font-semibold text-blue-600">Sieve</span> — Your AI-Powered Task Assistant for Telegram
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <p className="text-lg text-gray-700 leading-relaxed mb-16 text-center">
              Sieve is a Telegram bot that automatically extracts tasks from your group conversations using AI,
              understands deadlines in natural language, sends personal reminders directly to you before deadlines,
              and works for everyone in the group who subscribes.
            </p>

            <div className="space-y-6">
              <div className="flex items-start gap-6 p-6 bg-white backdrop-blur-sm rounded-lg shadow-sm hover:shadow-md transition-all duration-300 group">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-lg group-hover:scale-110 transition-transform duration-300">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-lg text-gray-800 leading-relaxed">Someone posts: "Submit the project report by Friday 5pm"</p>
                </div>
              </div>
              
              <div className="flex items-start gap-6 p-6 bg-white backdrop-blur-sm rounded-lg shadow-sm hover:shadow-md transition-all duration-300 group">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-cyan-100 flex items-center justify-center text-cyan-600 font-bold text-lg group-hover:scale-110 transition-transform duration-300">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-lg text-gray-800 leading-relaxed">Sieve automatically creates a task for all subscribers</p>
                </div>
              </div>
              
              <div className="flex items-start gap-6 p-6 bg-white backdrop-blur-sm rounded-lg shadow-sm hover:shadow-md transition-all duration-300 group">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-600 font-bold text-lg group-hover:scale-110 transition-transform duration-300">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-lg text-gray-800 leading-relaxed">You get reminders: 1 day before, 3 hours before, 30 mins before</p>
                </div>
              </div>
              
              <div className="flex items-start gap-6 p-6 bg-gradient-to-r from-blue-600 to-green-600 rounded-lg shadow-md group">
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-white flex items-center justify-center text-blue-600 font-bold text-lg group-hover:scale-110 transition-transform duration-300">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-lg text-white font-medium leading-relaxed">Never miss it</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
        </div>

        {/* How It Works Section */}
        <section id="how-it-works" className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600">
              Simple Setup, Automatic Results
            </p>
          </div>

          <div className="grid gap-12 md:grid-cols-3">
            <div className="relative p-8 bg-white backdrop-blur-sm border-2 border-gray-100 hover:border-blue-600 transition-all duration-300 rounded-lg group">
              <div className="absolute -top-4 -left-4 w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xl group-hover:scale-110 transition-transform duration-300">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </div>
              <h3 className="text-xl font-medium mb-4 mt-4">Add Sieve to Your Group</h3>
              <ul className="space-y-2 text-gray-700 leading-relaxed mb-6">
                <li>Click "Try Sieve Bot" button</li>
                <li>Add @sieve7_bot to your Telegram group</li>
                <li>Click "Enable My Reminders" button</li>
              </ul>
              <p className="text-xs text-gray-500 tracking-wide uppercase font-medium">Takes 30 seconds</p>
            </div>

            <div className="relative p-8 bg-white backdrop-blur-sm border-2 border-gray-100 hover:border-cyan-600 transition-all duration-300 rounded-lg group">
              <div className="absolute -top-4 -left-4 w-12 h-12 rounded-full bg-cyan-600 text-white flex items-center justify-center font-bold text-xl group-hover:scale-110 transition-transform duration-300">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </div>
              <h3 className="text-xl font-medium mb-4 mt-4">Let Sieve Listen</h3>
              <p className="text-gray-700 leading-relaxed mb-6">
                Sieve monitors your group messages for tasks and deadlines. It uses AI to understand natural language like
                "Submit form by tomorrow EOD", "Meeting on May 15 at 3pm", or "Deadline extended to next Monday".
              </p>
              <p className="text-xs text-gray-500 tracking-wide uppercase font-medium">Fully automatic</p>
            </div>

            <div className="relative p-8 bg-white backdrop-blur-sm border-2 border-gray-100 hover:border-green-600 transition-all duration-300 rounded-lg group">
              <div className="absolute -top-4 -left-4 w-12 h-12 rounded-full bg-green-600 text-white flex items-center justify-center font-bold text-xl group-hover:scale-110 transition-transform duration-300">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-medium mb-4 mt-4">Get Reminded</h3>
              <p className="text-gray-700 leading-relaxed mb-6">
                Sieve sends you personal reminders: 1 day before deadline, 3 hours before deadline,
                and 30 minutes before deadline.
              </p>
              <p className="text-xs text-gray-500 tracking-wide uppercase font-medium">Direct to your private chat</p>
            </div>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
        </div>

        {/* Features Section - Carousel */}
        <section id="features" className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              Features
            </h2>
            <p className="text-xl text-gray-600">
              Powerful Features, Zero Effort
            </p>
          </div>

          <div className="relative">
            <div className="overflow-hidden" ref={emblaRef}>
              <div className="flex gap-6">
                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white rounded"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">AI-Powered Extraction</h3>
                  <p className="text-gray-700 leading-relaxed">
                    Understands natural language. No special commands needed. Just chat normally in your group.
                  </p>
                </div>

                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-cyan-500 to-green-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white rounded-full"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">Smart Reminders</h3>
                  <p className="text-gray-700 leading-relaxed">
                    Multi-level reminders at 1 day, 3 hours, and 30 minutes. Sent directly to your private chat.
                    Never intrusive in the group.
                  </p>
                </div>

                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-green-500 to-blue-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white rounded-lg"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">Group-Wide Support</h3>
                  <p className="text-gray-700 leading-relaxed">
                    Everyone in the group can subscribe. Each person gets their own reminders. No coordination needed.
                  </p>
                </div>

                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-blue-500 to-green-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">Timezone Smart</h3>
                  <p className="text-gray-700 leading-relaxed">
                    Automatically handles IST timezone. Understands "EOD", "COB", "midnight". Converts times correctly.
                  </p>
                </div>

                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white rounded-full"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">Privacy First</h3>
                  <p className="text-gray-700 leading-relaxed">
                    Only processes messages in groups where it's added. No data sold or shared. Secure and reliable.
                  </p>
                </div>

                <div className="flex-[0_0_100%] md:flex-[0_0_50%] lg:flex-[0_0_33.333%] min-w-0 p-8 bg-white/60 backdrop-blur-sm hover:shadow-lg transition-all duration-300 rounded-lg border border-gray-100">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-green-500 to-cyan-500 flex items-center justify-center mb-6">
                    <div className="h-6 w-6 border-2 border-white rounded-lg"></div>
                  </div>
                  <h3 className="text-lg font-medium mb-3">Manage Your Tasks</h3>
                  <p className="text-gray-700 leading-relaxed">
                    View all your tasks with /tasks. Delete tasks with /delete. Edit deadlines with /edit.
                    Full control in private chat.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={scrollPrev}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 w-12 h-12 rounded-full bg-white shadow-lg flex items-center justify-center hover:bg-blue-600 hover:text-white transition-all duration-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            <button
              onClick={scrollNext}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 w-12 h-12 rounded-full bg-white shadow-lg flex items-center justify-center hover:bg-blue-600 hover:text-white transition-all duration-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </section>

        {/* Use Cases Section */}
        <section className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              Perfect For
            </h2>
            <p className="text-xl text-gray-500">
              Who Benefits from Sieve?
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2">
            <div className="relative pl-8 border-l-4 border-blue-600 hover:border-green-600 transition-colors duration-300 p-6">
              <h3 className="text-2xl font-medium mb-4">Students</h3>
              <p className="text-gray-600 leading-relaxed">
                Track assignment deadlines, project submissions, and exam schedules from your class groups
                without missing a beat.
              </p>
            </div>

            <div className="relative pl-8 border-l-4 border-cyan-600 hover:border-blue-600 transition-colors duration-300 p-6">
              <h3 className="text-2xl font-medium mb-4">Work Teams</h3>
              <p className="text-gray-600 leading-relaxed">
                Stay on top of deliverables, meetings, and client deadlines discussed in your team channels.
              </p>
            </div>

            <div className="relative pl-8 border-l-4 border-green-600 hover:border-cyan-600 transition-colors duration-300 p-6">
              <h3 className="text-2xl font-medium mb-4">Project Groups</h3>
              <p className="text-gray-600 leading-relaxed">
                Coordinate tasks and milestones across multiple collaborators without manual tracking.
              </p>
            </div>

            <div className="relative pl-8 border-l-4 border-blue-600 hover:border-green-600 transition-colors duration-300 p-6">
              <h3 className="text-2xl font-medium mb-4">Community Organizers</h3>
              <p className="text-gray-600 leading-relaxed">
                Manage event deadlines, volunteer tasks, and coordination for your community groups.
              </p>
            </div>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
        </div>

        {/* Why Sieve Section */}
        <section className="relative py-24 bg-gradient-to-br from-blue-50 to-green-50 -mx-6 md:-mx-12 lg:-mx-24 px-6 md:px-12 lg:px-24">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
                Why Sieve?
              </h2>
              <p className="text-xl text-gray-600">
                Compare Sieve with Manual Tracking and Calendar Apps
              </p>
            </div>

            <div className="overflow-x-auto bg-white rounded-lg shadow-sm p-8">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-blue-600">
                    <th className="pb-4 pr-8 font-medium">Feature</th>
                    <th className="pb-4 pr-8 font-medium">Manual Tracking</th>
                    <th className="pb-4 pr-8 font-medium">Calendar Apps</th>
                    <th className="pb-4 font-medium text-blue-600">Sieve</th>
                  </tr>
                </thead>
                <tbody className="text-gray-600">
                  <tr className="border-b border-gray-100 hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Automatic extraction</td>
                    <td className="py-4 pr-8">Copy-paste manually</td>
                    <td className="py-4 pr-8">Manual entry</td>
                    <td className="py-4 font-medium text-blue-600">Fully automatic</td>
                  </tr>
                  <tr className="border-b border-gray-100 hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Group integration</td>
                    <td className="py-4 pr-8">No integration</td>
                    <td className="py-4 pr-8">No integration</td>
                    <td className="py-4 font-medium text-blue-600">Native Telegram</td>
                  </tr>
                  <tr className="border-b border-gray-100 hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Natural language</td>
                    <td className="py-4 pr-8">Must format dates</td>
                    <td className="py-4 pr-8">Limited</td>
                    <td className="py-4 font-medium text-blue-600">Understands everything</td>
                  </tr>
                  <tr className="border-b border-gray-100 hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Multi-user support</td>
                    <td className="py-4 pr-8">Everyone does it separately</td>
                    <td className="py-4 pr-8">Separate calendars</td>
                    <td className="py-4 font-medium text-blue-600">One bot, all subscribers</td>
                  </tr>
                  <tr className="border-b border-gray-100 hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Setup time</td>
                    <td className="py-4 pr-8">Ongoing effort</td>
                    <td className="py-4 pr-8">5-10 mins per task</td>
                    <td className="py-4 font-medium text-blue-600">30 seconds one-time</td>
                  </tr>
                  <tr className="hover:bg-blue-50 transition-colors duration-200">
                    <td className="py-4 pr-8">Cost</td>
                    <td className="py-4 pr-8">Free but tedious</td>
                    <td className="py-4 pr-8">$5-15/month</td>
                    <td className="py-4 font-medium text-blue-600">Free</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
              <div className="group p-6">
                <div className="h-1 w-12 bg-gradient-to-r from-blue-600 to-cyan-600 mb-4 group-hover:w-20 transition-all duration-300"></div>
                <h3 className="text-lg font-medium mb-3">Zero Effort After Setup</h3>
                <p className="text-gray-600 leading-relaxed">
                  No manual entry, no copy-pasting. Just chat normally, Sieve handles the rest.
                </p>
              </div>

              <div className="group p-6">
                <div className="h-1 w-12 bg-gradient-to-r from-cyan-600 to-green-600 mb-4 group-hover:w-20 transition-all duration-300"></div>
                <h3 className="text-lg font-medium mb-3">Instant Deployment</h3>
                <p className="text-gray-600 leading-relaxed">
                  No app downloads, no account creation. Works right in Telegram where you already are.
                </p>
              </div>

              <div className="group p-6">
                <div className="h-1 w-12 bg-gradient-to-r from-green-600 to-blue-600 mb-4 group-hover:w-20 transition-all duration-300"></div>
                <h3 className="text-lg font-medium mb-3">Built for Groups</h3>
                <p className="text-gray-600 leading-relaxed">
                  Designed specifically for group chat workflows. Everyone benefits from one bot.
                </p>
              </div>

              <div className="group p-6">
                <div className="h-1 w-12 bg-gradient-to-r from-blue-600 to-green-600 mb-4 group-hover:w-20 transition-all duration-300"></div>
                <h3 className="text-lg font-medium mb-3">Completely Free</h3>
                <p className="text-gray-600 leading-relaxed">
                  No subscriptions, no hidden costs. Full features for everyone.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Technology Section */}
        <section className="relative py-24 max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
              Technology
            </h2>
            <p className="text-xl text-gray-500">
              Built with Modern AI and Reliable Infrastructure
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2">
            <div className="group relative overflow-hidden p-8 border-2 border-gray-100 hover:border-blue-600 transition-all duration-300 rounded-lg">
              <div className="absolute top-0 left-0 h-full w-1 bg-gradient-to-b from-blue-600 to-cyan-600 transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-top"></div>
              <h3 className="text-xl font-medium mb-4">AI-Powered Intelligence</h3>
              <p className="text-gray-600 leading-relaxed">
                Uses Groq LLM (Llama 3.1) for natural language understanding. Extracts tasks, deadlines,
                and action items automatically. Handles corrections and updates intelligently.
              </p>
            </div>

            <div className="group relative overflow-hidden p-8 border-2 border-gray-100 hover:border-cyan-600 transition-all duration-300 rounded-lg">
              <div className="absolute top-0 left-0 h-full w-1 bg-gradient-to-b from-cyan-600 to-green-600 transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-top"></div>
              <h3 className="text-xl font-medium mb-4">Fast and Reliable</h3>
              <p className="text-gray-600 leading-relaxed">
                Microservices architecture for scalability. Redis caching for instant responses.
                PostgreSQL for reliable data storage. RabbitMQ for message processing.
              </p>
            </div>

            <div className="group relative overflow-hidden p-8 border-2 border-gray-100 hover:border-green-600 transition-all duration-300 rounded-lg">
              <div className="absolute top-0 left-0 h-full w-1 bg-gradient-to-b from-green-600 to-blue-600 transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-top"></div>
              <h3 className="text-xl font-medium mb-4">Production-Ready</h3>
              <p className="text-gray-600 leading-relaxed">
                Kubernetes deployment with auto-scaling. Prometheus and Grafana monitoring.
                Automated backups and disaster recovery. 99.9% uptime target.
              </p>
            </div>

            <div className="group relative overflow-hidden p-8 border-2 border-gray-100 hover:border-blue-600 transition-all duration-300 rounded-lg">
              <div className="absolute top-0 left-0 h-full w-1 bg-gradient-to-b from-blue-600 to-green-600 transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-top"></div>
              <h3 className="text-xl font-medium mb-4">Secure and Private</h3>
              <p className="text-gray-600 leading-relaxed">
                Webhook signature verification. Database transactions for data integrity.
                Message deduplication to prevent duplicates. No data sharing with third parties.
              </p>
            </div>
          </div>
        </section>

        {/* Decorative Line */}
        <div className="relative py-16 max-w-7xl mx-auto">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-cyan-600/30 to-transparent"></div>
        </div>

        {/* Getting Started Section */}
        <section className="relative py-24 bg-gradient-to-br from-blue-600 to-green-600 text-white -mx-6 md:-mx-12 lg:-mx-24 px-6 md:px-12 lg:px-24">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-light tracking-tight mb-4">
                Get Started
              </h2>
              <p className="text-xl text-white/90">
                Ready to Never Miss a Deadline Again?
              </p>
            </div>

            <div className="grid gap-12 md:grid-cols-2 mb-20">
              <div className="border-2 border-white/30 p-8 hover:border-white/60 transition-colors duration-300 rounded-lg backdrop-blur-sm bg-white/10">
                <h3 className="text-2xl font-medium mb-6">For Individuals</h3>
                <ol className="space-y-3 text-white/90 leading-relaxed">
                  <li className="flex gap-3">
                    <span className="text-white font-medium">1.</span>
                    <span>Click the button below to open Sieve bot</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">2.</span>
                    <span>Send /start to the bot</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">3.</span>
                    <span>Add the bot to your group</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">4.</span>
                    <span>Click "Enable My Reminders"</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">5.</span>
                    <span>Done! You'll get reminders automatically</span>
                  </li>
                </ol>
              </div>

              <div className="border-2 border-white/30 p-8 hover:border-white/60 transition-colors duration-300 rounded-lg backdrop-blur-sm bg-white/10">
                <h3 className="text-2xl font-medium mb-6">For Group Admins</h3>
                <ol className="space-y-3 text-white/90 leading-relaxed">
                  <li className="flex gap-3">
                    <span className="text-white font-medium">1.</span>
                    <span>Add @sieve7_bot to your group</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">2.</span>
                    <span>Share the "Enable My Reminders" button with members</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">3.</span>
                    <span>Everyone who clicks it will get personal reminders</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="text-white font-medium">4.</span>
                    <span>That's it! No configuration needed</span>
                  </li>
                </ol>
              </div>
            </div>

            <div className="text-center">
              <a href="https://t.me/sieve7_bot" target="_blank" rel="noopener noreferrer">
                <Button className="rounded-full border-2 border-white bg-white px-12 py-6 text-lg text-blue-600 hover:bg-transparent hover:text-white transition-all duration-300 transform hover:scale-105 font-medium">
                  Start Using Sieve Now
                </Button>
              </a>

              <div className="mt-8 flex justify-center gap-10 text-sm text-white/80 tracking-wide">
                <span>Free forever</span>
                <span>No credit card required</span>
                <span>Setup in 30 seconds</span>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section id="faq" className="relative py-32">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-5xl font-light tracking-tight mb-24">
              Frequently Asked Questions
            </h2>

            <div className="space-y-12">
              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">Is Sieve really free?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Yes! Sieve is completely free to use with no hidden costs or subscriptions.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">Does Sieve read all my messages?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Sieve only processes messages in groups where it's been added. It looks for task-related content
                  and ignores everything else. Your privacy is our priority.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">What if I want to stop using Sieve?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Simply send /unsubscribe to the bot in private chat, or remove it from your group.
                  You can rejoin anytime.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">Can I use Sieve in multiple groups?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Absolutely! Add Sieve to as many groups as you want. You'll get reminders for tasks from all of them.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">What happens if someone corrects a deadline in the group?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Sieve's AI detects corrections and automatically updates the deadline for everyone.
                  No manual intervention needed.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">Can I manage my tasks?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Yes! Use /tasks to see all your tasks, /delete to remove tasks, and /edit to change deadlines—all
                  in private chat with the bot.
                </p>
              </div>

              <div className="group border-b border-gray-200 pb-8 hover:border-black transition-colors duration-300">
                <h3 className="text-2xl font-medium mb-4">What languages does Sieve support?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Currently, Sieve works best with English. Multi-language support is coming soon!
                </p>
              </div>

              <div className="group pb-8">
                <h3 className="text-2xl font-medium mb-4">How accurate is the AI?</h3>
                <p className="text-gray-600 leading-relaxed text-lg">
                  Sieve uses state-of-the-art AI (Llama 3.1) and is highly accurate. If it's unsure about something,
                  it will ask you for clarification.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Footer Section */}
        <footer className="relative py-24 border-t border-gray-200 mt-24 max-w-7xl mx-auto">
          <div className="grid gap-16 md:grid-cols-2">
            <div>
              <h3 className="text-3xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">Sieve</h3>
              <p className="text-gray-700 leading-relaxed text-lg mb-6">
                Never miss a deadline from your group chats.
              </p>
              <p className="text-sm text-gray-500">
                Made for students and teams everywhere.
              </p>
            </div>

            <div>
              <h3 className="text-xl font-medium mb-6 tracking-wide">QUICK LINKS</h3>
              <ul className="space-y-3 text-gray-700 text-lg">
                <li>
                  <a href="https://t.me/sieve7_bot" target="_blank" rel="noopener noreferrer" className="hover:text-blue-600 transition-colors duration-200">
                    Try Sieve Bot
                  </a>
                </li>
                <li>
                  <a href="#how-it-works" className="hover:text-blue-600 transition-colors duration-200">
                    How It Works
                  </a>
                </li>
                <li>
                  <a href="#features" className="hover:text-blue-600 transition-colors duration-200">
                    Features
                  </a>
                </li>
                <li>
                  <a href="#faq" className="hover:text-blue-600 transition-colors duration-200">
                    FAQ
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-20 pt-10 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-500 tracking-wide">© 2026 Sieve. All rights reserved.</p>
          </div>
        </footer>
      </main>
    </div>
  )
}
