import React, { useEffect, useRef } from "react";
import {
  Animated,
  PanResponder,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";

import type { Comment, VoteChoice } from "../types";

type SwipeCardProps = {
  comment: Comment;
  onVote: (choice: VoteChoice) => void;
};

const SWIPE_THRESHOLD = 110;
const VERTICAL_THRESHOLD = -100;

export function SwipeCard({ comment, onVote }: SwipeCardProps) {
  const { width } = useWindowDimensions();
  const position = useRef(new Animated.ValueXY()).current;

  useEffect(() => {
    position.setValue({ x: 0, y: 0 });
  }, [comment.id, position]);

  const forceSwipe = (choice: VoteChoice) => {
    let x = 0;
    let y = 0;
    if (choice === 1) {
      x = width;
    } else if (choice === -1) {
      x = -width;
    } else {
      y = -width;
    }
    Animated.timing(position, {
      toValue: { x, y },
      duration: 180,
      useNativeDriver: false,
    }).start(() => {
      position.setValue({ x: 0, y: 0 });
      onVote(choice);
    });
  };

  const resetPosition = () => {
    Animated.spring(position, {
      toValue: { x: 0, y: 0 },
      useNativeDriver: false,
    }).start();
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_evt, gestureState) =>
        Math.abs(gestureState.dx) > 4 || Math.abs(gestureState.dy) > 4,
      onPanResponderMove: Animated.event([null, { dx: position.x, dy: position.y }], {
        useNativeDriver: false,
      }),
      onPanResponderRelease: (_evt, gestureState) => {
        if (gestureState.dx > SWIPE_THRESHOLD) {
          forceSwipe(1);
          return;
        }
        if (gestureState.dx < -SWIPE_THRESHOLD) {
          forceSwipe(-1);
          return;
        }
        if (gestureState.dy < VERTICAL_THRESHOLD) {
          forceSwipe(0);
          return;
        }
        if (Math.abs(gestureState.dx) < 6 && Math.abs(gestureState.dy) < 6) {
          forceSwipe(0);
          return;
        }
        resetPosition();
      },
    })
  ).current;

  const rotate = position.x.interpolate({
    inputRange: [-width, 0, width],
    outputRange: ["-18deg", "0deg", "18deg"],
  });
  const agreeOpacity = position.x.interpolate({
    inputRange: [0, SWIPE_THRESHOLD],
    outputRange: [0, 1],
    extrapolate: "clamp",
  });
  const disagreeOpacity = position.x.interpolate({
    inputRange: [-SWIPE_THRESHOLD, 0],
    outputRange: [1, 0],
    extrapolate: "clamp",
  });

  return (
    <Animated.View
      style={[
        styles.card,
        {
          transform: [{ translateX: position.x }, { translateY: position.y }, { rotate }],
        },
      ]}
      {...panResponder.panHandlers}
    >
      <View style={styles.badges}>
        <Animated.Text style={[styles.badge, styles.badgeDisagree, { opacity: disagreeOpacity }]}>
          Disagree
        </Animated.Text>
        <Animated.Text style={[styles.badge, styles.badgeAgree, { opacity: agreeOpacity }]}>
          Agree
        </Animated.Text>
      </View>
      <Text style={styles.text}>{comment.text}</Text>
      <View style={styles.counts}>
        <Text style={styles.countText}>👍 {comment.agree_count ?? 0}</Text>
        <Text style={styles.countText}>👎 {comment.disagree_count ?? 0}</Text>
        <Text style={styles.countText}>➖ {comment.pass_count ?? 0}</Text>
      </View>
      <Text style={styles.hint}>Swipe right/left/up or tap to pass.</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#111827",
    borderColor: "#1f2937",
    borderWidth: 1,
    borderRadius: 16,
    minHeight: 300,
    padding: 16,
    justifyContent: "space-between",
  },
  badges: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  badge: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 4,
    fontWeight: "700",
    overflow: "hidden",
  },
  badgeAgree: {
    color: "#22c55e",
    borderColor: "#22c55e",
  },
  badgeDisagree: {
    color: "#ef4444",
    borderColor: "#ef4444",
  },
  text: {
    color: "#e5e7eb",
    fontSize: 22,
    lineHeight: 30,
    fontWeight: "600",
  },
  counts: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  countText: {
    color: "#94a3b8",
    fontSize: 14,
  },
  hint: {
    color: "#64748b",
    fontSize: 12,
    textAlign: "center",
  },
});
