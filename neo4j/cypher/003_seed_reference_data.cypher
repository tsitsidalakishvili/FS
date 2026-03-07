// Optional seed for baseline taxonomy/reference nodes.
// Safe to run multiple times.

UNWIND ["Supporter", "Member"] AS supporterType
MERGE (st:SupporterType {name: supporterType})
ON CREATE SET st.createdAt = datetime()
SET st.updatedAt = datetime();

UNWIND ["Fundraising", "Data", "Organizing", "Field Outreach", "Communications"] AS skillName
MERGE (:Skill {name: skillName});

UNWIND ["Phone Banking", "Door Knocking", "Digital Campaigns", "Policy", "Fundraising"] AS areaName
MERGE (:InvolvementArea {name: areaName});

UNWIND ["High School", "Bachelor", "Master", "PhD"] AS educationName
MERGE (:EducationLevel {name: educationName});

UNWIND ["High Priority", "Volunteer", "Donor", "At Risk", "Follow-up Needed"] AS tagName
MERGE (:Tag {name: tagName});
