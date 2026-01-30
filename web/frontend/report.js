/**
 * Report Renderer - Displays assessment report with visual elements
 */

class ReportRenderer {
    constructor() {
        this.reportOverlay = document.getElementById('reportOverlay');
        this.CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
        this.currentReport = null;
    }

    /**
     * Show the report overlay with assessment data
     */
    showReport(assessmentData) {
        console.log('📊 Rendering assessment report:', assessmentData);
        this.currentReport = assessmentData;
        
        // Render all sections
        this.renderHeader(assessmentData);
        this.renderBadge(assessmentData.report.proficiency_level);
        this.renderCeiling(assessmentData.report);
        this.renderSkillAnalysis(assessmentData.report.domain_analyses);
        this.renderStrategy(assessmentData.report);
        
        // Show overlay with fade-in animation
        this.reportOverlay.style.display = 'block';
        setTimeout(() => {
            this.reportOverlay.classList.add('active');
        }, 50);
    }

    /**
     * Hide the report overlay
     */
    hideReport() {
        this.reportOverlay.classList.remove('active');
        setTimeout(() => {
            this.reportOverlay.style.display = 'none';
        }, 500);
    }

    /**
     * Render the header section
     */
    renderHeader(data) {
        const subtitle = document.getElementById('reportSubtitle');
        const ref = document.getElementById('reportRef');
        
        // Format date
        const date = new Date(data.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
        
        subtitle.textContent = `Korean Assessment • ${formattedDate}`;
        ref.textContent = `REF: ${data.session_id.split('-')[0]}`;
    }

    /**
     * Render the badge section with CEFR level
     */
    renderBadge(proficiencyLevel) {
        const badgeLevel = document.getElementById('badgeLevel');
        const badgeDescription = document.getElementById('badgeDescription');
        const cefrLabels = document.getElementById('cefrLabels');
        const cefrFill = document.getElementById('cefrFill');
        
        // Extract short level (e.g., "B1" from "B1 (Intermediate)")
        const shortLevel = proficiencyLevel.split(' ')[0];
        const levelIndex = this.CEFR_LEVELS.indexOf(shortLevel);
        
        badgeLevel.textContent = shortLevel;
        badgeDescription.textContent = proficiencyLevel;
        
        // Render CEFR labels
        cefrLabels.innerHTML = this.CEFR_LEVELS.map((level, idx) => {
            const isActive = idx === levelIndex;
            return `<span class="cefr-label ${isActive ? 'active' : ''}">${level}</span>`;
        }).join('');
        
        // Animate progress bar
        const progress = ((levelIndex + 1) / this.CEFR_LEVELS.length) * 100;
        setTimeout(() => {
            cefrFill.style.width = `${progress}%`;
        }, 300);
    }

    /**
     * Render the ceiling analysis section
     */
    renderCeiling(report) {
        const ceilingBadge = document.getElementById('ceilingBadge');
        const ceilingText = document.getElementById('ceilingText');
        
        ceilingBadge.textContent = `CEILING: ${report.ceiling_phase}`;
        ceilingText.textContent = `"${report.ceiling_analysis}"`;
    }

    /**
     * Render the skill analysis section with radar chart and domain cards
     */
    renderSkillAnalysis(domainAnalyses) {
        this.renderRadarChart(domainAnalyses);
        this.renderDomainCards(domainAnalyses);
    }

    /**
     * Render radar chart using SVG
     */
    renderRadarChart(domains) {
        const svg = document.getElementById('radarChart');
        const centerX = 150;
        const centerY = 150;
        const maxRadius = 110;
        const levels = 5;
        
        // Clear existing content
        svg.innerHTML = '';
        
        // Draw grid circles
        for (let i = 1; i <= levels; i++) {
            const radius = (maxRadius / levels) * i;
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', centerX);
            circle.setAttribute('cy', centerY);
            circle.setAttribute('r', radius);
            circle.setAttribute('fill', 'none');
            circle.setAttribute('stroke', 'rgba(255, 255, 255, 0.08)');
            circle.setAttribute('stroke-width', '1');
            svg.appendChild(circle);
        }
        
        // Calculate angles for each domain
        const numDomains = domains.length;
        const angleStep = (Math.PI * 2) / numDomains;
        
        // Draw axes and labels
        domains.forEach((domain, index) => {
            const angle = angleStep * index - Math.PI / 2; // Start from top
            const x = centerX + Math.cos(angle) * maxRadius;
            const y = centerY + Math.sin(angle) * maxRadius;
            
            // Draw axis line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', centerX);
            line.setAttribute('y1', centerY);
            line.setAttribute('x2', x);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', 'rgba(255, 255, 255, 0.08)');
            line.setAttribute('stroke-width', '1');
            svg.appendChild(line);
            
            // Draw label
            const labelDistance = maxRadius + 25;
            const labelX = centerX + Math.cos(angle) * labelDistance;
            const labelY = centerY + Math.sin(angle) * labelDistance;
            
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', labelX);
            text.setAttribute('y', labelY);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.setAttribute('fill', '#94A3B8');
            text.setAttribute('font-size', '11');
            text.setAttribute('font-weight', '500');
            text.textContent = domain.domain;
            svg.appendChild(text);
        });
        
        // Draw data polygon
        const points = domains.map((domain, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const rating = domain.rating;
            const radius = (maxRadius / 5) * rating;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            return `${x},${y}`;
        }).join(' ');
        
        // Data area (filled)
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', points);
        polygon.setAttribute('fill', 'rgba(139, 92, 246, 0.25)');
        polygon.setAttribute('stroke', '#A78BFA');
        polygon.setAttribute('stroke-width', '2');
        svg.appendChild(polygon);
        
        // Data points (dots)
        domains.forEach((domain, index) => {
            const angle = angleStep * index - Math.PI / 2;
            const rating = domain.rating;
            const radius = (maxRadius / 5) * rating;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', '4');
            circle.setAttribute('fill', '#A78BFA');
            svg.appendChild(circle);
        });
    }

    /**
     * Render domain cards (expandable)
     */
    renderDomainCards(domains) {
        const container = document.getElementById('domainCards');
        
        container.innerHTML = domains.map((domain, index) => {
            const ratingBars = Array.from({ length: 5 }, (_, i) => {
                const filled = i < domain.rating ? 'filled' : '';
                return `<div class="rating-bar ${filled}"></div>`;
            }).join('');
            
            return `
                <div class="domain-card" data-domain="${domain.domain}">
                    <div class="domain-card-header">
                        <div class="domain-card-left">
                            <span class="domain-name">${domain.domain}</span>
                            <div class="domain-rating">${ratingBars}</div>
                        </div>
                        <svg class="domain-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                    <div class="domain-card-body">
                        <p class="domain-observation">${domain.observation}</p>
                        <div class="domain-evidence">
                            <p class="evidence-label">Live Evidence</p>
                            <p class="evidence-text">${domain.evidence}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click handlers for expansion
        container.querySelectorAll('.domain-card').forEach(card => {
            card.addEventListener('click', () => {
                card.classList.toggle('expanded');
            });
        });
    }

    /**
     * Render strategy section
     */
    renderStrategy(report) {
        const strategyText = document.getElementById('strategyText');
        const strategyModuleText = document.getElementById('strategyModuleText');
        
        strategyText.textContent = report.optimization_strategy;
        strategyModuleText.textContent = report.starting_module;
    }

    /**
     * Setup CTA button click handler
     */
    setupCTAHandler(onCTAClick) {
        const ctaButton = document.getElementById('strategyCTA');
        ctaButton.addEventListener('click', () => {
            console.log('🎯 CTA button clicked');
            if (onCTAClick) {
                onCTAClick();
            }
        });
    }
}
