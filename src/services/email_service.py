"""
SendGrid Email Service
Handles all email communications for the beta program
"""

import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SendGrid"""
    
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'beta@brikk.ai')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Brikk AI')
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not set - emails will not be sent")
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        retries: int = 3
    ) -> bool:
        """
        Send an email with retry logic
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            retries: Number of retry attempts for transient failures
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.error(f"Cannot send email - SendGrid not configured")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            # Send with retry logic
            for attempt in range(retries):
                try:
                    response = self.client.send(message)
                    
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"Email sent successfully to {to_email}: {subject}")
                        return True
                    elif response.status_code >= 500:
                        # Server error - retry
                        logger.warning(f"SendGrid server error (attempt {attempt + 1}/{retries}): {response.status_code}")
                        if attempt < retries - 1:
                            continue
                    else:
                        # Client error - don't retry
                        logger.error(f"SendGrid client error: {response.status_code} - {response.body}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error sending email (attempt {attempt + 1}/{retries}): {str(e)}")
                    if attempt < retries - 1:
                        continue
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_application_received(
        self,
        to_email: str,
        name: str,
        application_id: int,
        queue_position: int
    ) -> bool:
        """
        Send confirmation email when application is received
        
        Args:
            to_email: Applicant's email
            name: Applicant's name
            application_id: Application ID
            queue_position: Position in review queue
            
        Returns:
            True if email sent successfully
        """
        subject = "Your Brikk Beta Application - Received!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .info-box {{
                    background: white;
                    padding: 20px;
                    border-left: 4px solid #4D82E8;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Application Received!</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                
                <p>Thank you for applying to the Brikk AI private beta program! We're excited to have you on board.</p>
                
                <div class="info-box">
                    <strong>Application Details:</strong><br>
                    Application ID: <strong>#{application_id}</strong><br>
                    Queue Position: <strong>#{queue_position}</strong><br>
                    Estimated Review Time: <strong>24-48 hours</strong>
                </div>
                
                <h3>What Happens Next?</h3>
                <ol>
                    <li><strong>Review</strong> - Our team will review your application within 24-48 hours</li>
                    <li><strong>Approval</strong> - If approved, you'll receive your API key and onboarding instructions</li>
                    <li><strong>Onboarding</strong> - Follow our quickstart guide to make your first API call in under 10 minutes</li>
                    <li><strong>Build</strong> - Start building amazing AI agent applications with Brikk!</li>
                </ol>
                
                <h3>Join Our Community</h3>
                <p>While you wait, join our Discord community to connect with other developers and the Brikk team:</p>
                <a href="https://discord.gg/brikk-ai" class="button">Join Discord →</a>
                
                <h3>Learn More</h3>
                <p>Check out our documentation to get a head start:</p>
                <ul>
                    <li><a href="https://brikk-infrastructure.onrender.com/docs">API Documentation</a></li>
                    <li><a href="https://brikk-infrastructure.onrender.com/docs/quickstart">Quickstart Guide</a></li>
                    <li><a href="https://brikk-infrastructure.onrender.com/marketplace">Agent Marketplace</a></li>
                </ul>
                
                <p>We'll be in touch soon!</p>
                
                <p>Best regards,<br>
                <strong>The Brikk Team</strong></p>
            </div>
            <div class="footer">
                <p>Brikk AI - The Economic Infrastructure for AI Agents</p>
                <p>Questions? Reply to this email or reach out on Discord.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {name},
        
        Thank you for applying to the Brikk AI private beta program!
        
        Application Details:
        - Application ID: #{application_id}
        - Queue Position: #{queue_position}
        - Estimated Review Time: 24-48 hours
        
        What Happens Next?
        1. Review - Our team will review your application within 24-48 hours
        2. Approval - If approved, you'll receive your API key and onboarding instructions
        3. Onboarding - Follow our quickstart guide to make your first API call
        4. Build - Start building amazing AI agent applications with Brikk!
        
        Join our Discord community: https://discord.gg/brikk-ai
        
        Learn more:
        - API Documentation: https://brikk-infrastructure.onrender.com/docs
        - Quickstart Guide: https://brikk-infrastructure.onrender.com/docs/quickstart
        - Agent Marketplace: https://brikk-infrastructure.onrender.com/marketplace
        
        We'll be in touch soon!
        
        Best regards,
        The Brikk Team
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_application_approved(
        self,
        to_email: str,
        name: str,
        api_key: str,
        application_id: int,
        portal_url: str = None,
        playground_url: str = None
    ) -> bool:
        """
        Send approval email with API key
        
        Args:
            to_email: Applicant's email
            name: Applicant's name
            api_key: Generated API key (shown only once!)
            application_id: Application ID
            
        Returns:
            True if email sent successfully
        """
        subject = "🎉 Welcome to Brikk Beta - Your API Key Inside!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .api-key {{
                    background: #1E1E1E;
                    color: #4D82E8;
                    padding: 20px;
                    border-radius: 5px;
                    font-family: monospace;
                    font-size: 14px;
                    word-break: break-all;
                    margin: 20px 0;
                    border: 2px solid #4D82E8;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 5px;
                }}
                .code-block {{
                    background: #1E1E1E;
                    color: #E0E0E0;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: monospace;
                    font-size: 13px;
                    overflow-x: auto;
                    margin: 15px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Welcome to Brikk Beta!</h1>
                <p>You're approved! Let's build the future of AI agents together.</p>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                
                <p>Congratulations! Your application has been approved. You now have full access to the Brikk AI platform during our private beta.</p>
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> This is your API key. Save it securely - you won't be able to see it again!
                </div>
                
                <div class="api-key">
                    <strong>Your API Key:</strong><br>
                    {api_key}
                </div>
                
                <h3>🚀 Quick Start (10 Minutes to First Call)</h3>
                
                <p><strong>Step 1:</strong> Install the Brikk SDK</p>
                <div class="code-block">
pip install brikk
# or
npm install @brikk/sdk
                </div>
                
                <p><strong>Step 2:</strong> Make your first API call</p>
                <div class="code-block">
from brikk import Brikk

client = Brikk(api_key="{api_key}")

# Register your first agent
agent = client.agents.create(
    name="My First Agent",
    description="A test agent",
    endpoint_url="https://your-agent.com/api"
)

print(f"Agent created: {{agent.id}}")
                </div>
                
                <p><strong>Step 3:</strong> Explore the marketplace</p>
                <div class="code-block">
# Discover available agents
agents = client.marketplace.list_agents()
for agent in agents:
    print(f"{{agent.name}}: {{agent.description}}")
                </div>
                
                <h3>🎯 Get Started Now</h3>
                <p>Click these magic links to access your personalized developer portal and try our demo playground:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{portal_url or '#'}" class="button" style="font-size: 16px; padding: 15px 40px;">🚀 Open Developer Portal</a>
                    <br><br>
                    <a href="{playground_url or '#'}" class="button" style="font-size: 16px; padding: 15px 40px;">🎮 Launch Demo Playground</a>
                </div>
                <div class="warning" style="margin-top: 20px;">
                    <strong>ℹ️ About Magic Links:</strong> Your magic links open a 45-minute session to the Developer Portal and Demo Playground. For agent calls in the playground, you'll use the API key shown in the portal (or you can paste it when prompted in the playground).
                </div>
                <p style="color: #666; font-size: 13px; text-align: center;">These links are valid for 45 minutes and provide instant access without additional login.</p>
                
                <h3>📚 Resources</h3>
                <a href="https://brikk-infrastructure.onrender.com/docs/quickstart" class="button">Quickstart Guide →</a>
                <a href="https://brikk-infrastructure.onrender.com/docs" class="button">API Docs →</a>
                <a href="https://brikk-infrastructure.onrender.com/marketplace" class="button">Marketplace →</a>
                
                <h3>💬 Join Office Hours</h3>
                <p>We host weekly office hours where you can ask questions, get help, and connect with other beta users:</p>
                <ul>
                    <li><strong>When:</strong> Every Wednesday at 2 PM PT</li>
                    <li><strong>Where:</strong> Discord #office-hours channel</li>
                    <li><strong>What:</strong> Live Q&A, demos, and community building</li>
                </ul>
                <a href="https://discord.gg/brikk-ai" class="button">Join Discord →</a>
                
                <h3>🎁 Beta Benefits</h3>
                <ul>
                    <li>✅ Free, unlimited API access during beta</li>
                    <li>✅ Direct access to the founding team</li>
                    <li>✅ Early access to new features</li>
                    <li>✅ Recognition as a founding developer</li>
                    <li>✅ Shape our roadmap with your feedback</li>
                </ul>
                
                <p>We can't wait to see what you build!</p>
                
                <p>Best regards,<br>
                <strong>The Brikk Team</strong></p>
            </div>
            <div class="footer">
                <p>Brikk AI - The Economic Infrastructure for AI Agents</p>
                <p>Questions? Reply to this email or reach out on Discord.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {name},
        
        Congratulations! Your application has been approved.
        
        YOUR API KEY (save this securely - you won't see it again):
        {api_key}
        
        Quick Start (10 Minutes to First Call):
        
        Step 1: Install the Brikk SDK
        pip install brikk
        # or
        npm install @brikk/sdk
        
        Step 2: Make your first API call
        from brikk import Brikk
        client = Brikk(api_key="{api_key}")
        agent = client.agents.create(name="My First Agent", ...)
        
        Step 3: Explore the marketplace
        agents = client.marketplace.list_agents()
        
        Get Started Now:
        - Developer Portal: {portal_url or 'Check your email for the link'}
        - Demo Playground: {playground_url or 'Check your email for the link'}
        
        About Magic Links:
        Your magic links open a 45-minute session to the Developer Portal and Demo Playground.
        For agent calls in the playground, you'll use the API key shown in the portal
        (or you can paste it when prompted in the playground).
        
        Resources:
        - Quickstart Guide: https://brikk-infrastructure.onrender.com/docs/quickstart
        - API Docs: https://brikk-infrastructure.onrender.com/docs
        - Marketplace: https://brikk-infrastructure.onrender.com/marketplace
        
        Join Office Hours:
        - When: Every Wednesday at 2 PM PT
        - Where: Discord #office-hours channel
        - Join: https://discord.gg/brikk-ai
        
        Beta Benefits:
        - Free, unlimited API access during beta
        - Direct access to the founding team
        - Early access to new features
        - Recognition as a founding developer
        - Shape our roadmap with your feedback
        
        We can't wait to see what you build!
        
        Best regards,
        The Brikk Team
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_application_rejected(
        self,
        to_email: str,
        name: str,
        application_id: int
    ) -> bool:
        """
        Send polite rejection email
        
        Args:
            to_email: Applicant's email
            name: Applicant's name
            application_id: Application ID
            
        Returns:
            True if email sent successfully
        """
        subject = "Brikk Beta Application Update"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(45deg, #4D82E8, #A355E8);
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 5px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Thank You for Your Interest</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                
                <p>Thank you for your interest in the Brikk AI private beta program. We've reviewed your application and unfortunately, we're unable to offer you a spot in this round of our beta program.</p>
                
                <p>Due to high demand and limited capacity, we're being very selective about who we invite to ensure we can provide the best possible experience for our beta users.</p>
                
                <h3>Stay Connected</h3>
                <p>We'd love to keep you in the loop! Here's how you can stay connected:</p>
                
                <ul>
                    <li><strong>Join our Discord:</strong> Connect with the community and stay updated on announcements</li>
                    <li><strong>Follow our documentation:</strong> Learn about Brikk's capabilities and prepare for future access</li>
                    <li><strong>Apply again later:</strong> We'll be opening more beta slots in the coming months</li>
                </ul>
                
                <a href="https://discord.gg/brikk-ai" class="button">Join Discord →</a>
                <a href="https://brikk-infrastructure.onrender.com/docs" class="button">View Docs →</a>
                
                <h3>Public Launch Coming Soon</h3>
                <p>We're planning a public launch in the near future. When we do, you'll be among the first to know!</p>
                
                <p>Thank you again for your interest in Brikk. We hope to work with you in the future.</p>
                
                <p>Best regards,<br>
                <strong>The Brikk Team</strong></p>
            </div>
            <div class="footer">
                <p>Brikk AI - The Economic Infrastructure for AI Agents</p>
                <p>Questions? Reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {name},
        
        Thank you for your interest in the Brikk AI private beta program.
        
        We've reviewed your application and unfortunately, we're unable to offer you a spot in this round of our beta program. Due to high demand and limited capacity, we're being very selective to ensure the best experience for our beta users.
        
        Stay Connected:
        - Join our Discord: https://discord.gg/brikk-ai
        - View our documentation: https://brikk-infrastructure.onrender.com/docs
        - Apply again later when we open more beta slots
        
        Public Launch Coming Soon:
        We're planning a public launch in the near future, and you'll be among the first to know!
        
        Thank you again for your interest in Brikk.
        
        Best regards,
        The Brikk Team
        """
        
        return self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    """Get or create the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

