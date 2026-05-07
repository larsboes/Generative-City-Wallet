---
summary: "CISO here and this case has been living rent free in my head. In case you missed, Air Canada's chatbot told a customer he could get a bereav"
reviewed:
done:
related:
sources:
  - "https://www.reddit.com/r/ciso/comments/1s5gl21/air_canadas_chatbot_gave_a_customer_wrong_info/"
---
CISO here and this case has been living rent free in my head. In case you missed, Air Canada's chatbot told a customer he could get a bereavement refund within 90 days. He booked flights based on that.

Chatbot was wrong. Customer sued. Air Canada argued the chatbot was a separate legal entity. Judge said thats nonsense, you are responsible for everything on yr website.

Now think about how many companies deployed customer-facing AI this year alone. Chatbots giving policy info, pricing, health guidance. How many were adversarially tested for misinformation?

This is a liability problem not a UX problem. What adversarial works for customer facing AI before something like this happens?

---

## Comments

> **Ill-Database4116** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocuwzua/) · 6 points
> 
> Followed this case, the legal precedent here is massive. The judge said it doesnt matter whether information comes from a static page or a chatbot , the company is responsible for all of it.
> 
> Every company running a customer facing AI just inherited liability for every answer it gives. If you havent stress-tested your AI for misinformation in your specific domain, yr gambling with your legal budget.
> 
> we started using alice's caterpillar tool to scan our customer-facing AI for misinformation risks before deployment. catches things our internal testing missed, especially the subtle domain-specific stuff that generic red-teaming misses.
> 
> > **MysteriousAwards** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocvd1r0/) · 2 points
> > 
> > I mean - I bet you're already holding bug bounty reporters accountable for whatever LLM-generated submission they send you to the same standard. Why is this surprising to anyone?

> **SuitableFan6634** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocuejax/) · 7 points
> 
> I'm not. I'm accountable for cyber and information security, not data governance.
> 
> > **thomasclifford** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocuhaxg/) · 1 points
> > 
> > I think in some way still falls under CISO, atleast at my org. Anyway, thoughts?
> > 
> > > **MysteriousAwards** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocvc04f/) · 3 points
> > > 
> > > Lol what? Technology deployed that misrepresents your product is not entirely a security issue (unless caused by an exploit but if your AI helper isn't learning based on user input you're fine). Any team trying to blame your department for it is just looking to use you as a scapegoat. Your anxiety in response tells me you get holding the bag for shit that isn't your responsibility more often than you should.
> > > 
> > > Push back - the dolts that accept the risk of using untested technology are accountable.
> > > 
> > > My advice - any time people want to go out of policy, say - have your department's exec sign that they accepted the risk, so when shit inevitably hits the fan, you point the pack of wolves their way.
> > > 
> > > > **Logical-Design-8334** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocvuhjf/) · 1 points
> > > > 
> > > > You’re not wrong in principle, but sadly a lot of companies will still blame the ciso regardless of what is on paper owning the risk. It’s a maturity and cultural item, and if the ciso reports to the cio or cto, the likelihood of this happening increases; also smaller orgs tend towards this.
> > > > 
> > > > > **MysteriousAwards** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocwktc3/) · 1 points
> > > > > 
> > > > > You make it sound like the individual in a CISO role, and the company has fixed things outside of your control. If you’re a CISO and not managing this conversation or expectation of course then you’re going to get managed by people who don’t have a clue what they’re doing.
> > > 
> > > > **Julian\_Sark** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocxgjgg/) · 1 points
> > > > 
> > > > I have been in pricy CISO/ISO trainings by the German de-facto standardization org, and they claim that CISO is responsible for any and all breaches, unavailability and ABUSE involving technological systems. I do not share this view, but it's certainly out there and I had to adopt it to pass the exam.
> > 
> > > **SuitableFan6634** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocup66c/) · 1 points
> > > 
> > > Have you also taken on data lifecycle management / destruction?

> **South-Opening-9720** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocuwa3n/) · 2 points
> 
> yeah this is exactly why policy answers need hard rails. if the bot is speaking on your site, it is your policy surface whether the model guessed or not. i use chat data and the only setup i trust for this is grounded answers plus a clear fallback to human handoff when confidence is shaky. are you testing against refund and exception scenarios specifically, or mostly generic jailbreaks?

> **MortgageWarm3770** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocux4vs/) · 2 points
> 
> Air Canada tried to argue the chatbot was a separate legal entity. The judge destroyed that argument. This should be a wake-up call for every product and legal team.
> 
> If your AI says it, your company owns it. The only responsible approach is rigorous predeployment testing with people who know how to find the failure modes that lead to harm. Not just technical failures,,, even business context failures.

> **Julian\_Sark** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocxgs7y/) · 2 points
> 
> Counter question: How do you prevent an underpaid, possibly third party employee in a foreign call center reading off of scripts from promising the customer undue rebates? Tech is (currently) as imperfect as people; whichever department decides to save cost, by replacing well-trained people with poorly trained people, or by replacing people with AI, knows, and bears, the risk.
> 
> > **manapause** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/oczh7fq/) · 1 points
> > 
> > Of course this has happened multiple times and will happen again, and will continue to happen. But there’s a difference between learning from your mistakes, and “this is why we can’t have nice things.”
> > 
> > The Kaiser Permanente phone triage lawsuit in Colorado is the first thing that popped up in my mind when I read OP. There are incredible nuances that must be accounted for. while this feels like wild new territory, it’s really just introducing processes and creating safeguards and injecting humans where you need them.
> > 
> > That said, because, nobody wants to move slow in this space - so therefore handfuls of travelers at a time are going to have the travel plans turned inside out because defining your edge cases are just too laborious for the stakes.

> **South-Opening-9720** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocvrxio/) · 1 points
> 
> The biggest thing is forcing policy answers to come from approved source material instead of freehand generation. If the model can’t cite the internal policy or the grounding is weak, it should refuse or escalate. That’s where chat data is useful for reviewing failure patterns after the fact, but I’d still treat anything customer-facing like a controlled system, not a smart FAQ.

> **fightmilk22** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocwfe3e/) · 1 points
> 
> Companies giving out false info to get a sale and then saying the AI messed up can quickly get out of hand. Why should a company get a pass for lying to customers?

> **samstone\_** · [2026-04-02](https://reddit.com/r/ciso/comments/1s5gl21/comment/odtgk69/) · 1 points
> 
> Oh yeah, let’s make this a CISO thing. Give me a break. What’s with the wannabe land grab. Need another topic for a talk at the next conference or something.

> **samstone\_** · [2026-04-02](https://reddit.com/r/ciso/comments/1s5gl21/comment/odtgufm/) · 1 points
> 
> Another point - we live in a post-precedence world. Every case will be continue to be unique and set even more precedence. This is NOT going to be an epidemic.

> **proigor1024** · [2026-03-27](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocuwpim/) · \-1 points
> 
> > they got sued for it
> 
> adversarial testing before deployment isnt optional anymore. You need people who will ask your chatbot every weird, ambiguous, edge case question a real customer would ask. Used to do this internally, which was very innefective and wasted too much of our time. Now we outsource that to Alice, they know their way around Ai red teaming and runtime security.
> 
> > **MysteriousAwards** · [2026-03-28](https://reddit.com/r/ciso/comments/1s5gl21/comment/ocvcsu4/) · 2 points
> > 
> > You're just paying a consultancy at that point to have a neck on hand to offer whenever this goes sideways. LLMs are non-deterministic, and using them to represent policy data is a high-wire act.
> > 
> > Mitigate by having human-backed management of these systems rather than pretending the tech is more mature than it is and putting your head in the sand.

> **razrcallahan** · [2026-04-13](https://reddit.com/r/ciso/comments/1s5gl21/comment/ofwvjfq/) · 1 points
> 
> The legal precedent here matters more than the chatbot itself. Air Canada's "separate legal entity" argument got rejected immediately, which means every AI deployment is now a direct liability exposure, not a compartmentalized risk.
> 
> The question shifts from "can our AI hallucinate?" (yes, all of them can) to "can we demonstrate in court that we had reasonable controls in place?" That requires output logs, policy enforcement records, and evidence that you had human oversight mechanisms.
> 
> An acceptable use policy in an internal doc doesn't count. You need technical evidence that the system was operating within defined parameters.